import os
import glob
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from services.skill_testing.core.llm_client import OpenAIClient
from services.skill_testing.core.skill_client import SkillExecutionClient
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.benchmark_runner import (
    WorkspaceManager,
    BugInjector,
    PreValidator,
    run_baseline_a,
    run_baseline_b,
    run_cass_orchestrator,
    verify_solution
)

# Available mock tools index to build the semantic registry
MOCK_TOOLS_LIST = [
    {"name": "analyze-stacktrace", "description": "Phân tích java stacktrace", "skill_id": "analyze-stacktrace"},
    {"name": "read-code-context", "description": "Đọc mã nguồn Java xung quanh dòng chỉ định", "skill_id": "read-code-context"},
    {"name": "suggest-java-fix", "description": "Ghi đè bản vá lỗi Java", "skill_id": "suggest-java-fix"},
    {"name": "debug-java-null-pointer", "description": "Biên dịch javac kiểm tra lỗi cú pháp Java", "skill_id": "debug-java-null-pointer"},
    {"name": "debug-python-error", "description": "Phân tích lỗi Python và sửa", "skill_id": "debug-python-error"},
    {"name": "suggest-python-fix", "description": "Vá lỗi Python", "skill_id": "suggest-python-fix"}
]

async def run_benchmark():
    print("================================================================================")
    print("⚡ [BENCHMARK RUNNER] Starting AI Software Engineering Agent Benchmark Suite ⚡")
    print("================================================================================\n")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ [ERROR] OPENAI_API_KEY environment variable is not set. Aborting benchmark.")
        return
        
    # Initialize components
    ws_manager = WorkspaceManager()
    bug_injector = BugInjector()
    llm_client = OpenAIClient(api_key=api_key)
    
    # Build Semantic Registry index
    semantic_registry.build_index(MOCK_TOOLS_LIST)
    
    # Load all testcases
    testcases_dir = os.path.join(os.path.dirname(__file__), "testcases")
    tc_dirs = glob.glob(os.path.join(testcases_dir, "TC_*"))
    
    if not tc_dirs:
        print(f"❌ No testcases found under: {testcases_dir}")
        return
        
    print(f"🧪 Found {len(tc_dirs)} testcases to execute.")
    
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_str = datetime.now().isoformat() + "Z"
    
    results_detail = []
    summary_metrics = {
        "pure_llm": {"passed": 0, "total": 0, "latency_sum_ms": 0, "tokens_sum": 0, "cost_sum_usd": 0.0},
        "top1_similarity": {"passed": 0, "total": 0, "latency_sum_ms": 0, "tokens_sum": 0, "cost_sum_usd": 0.0},
        "cass_orchestrator": {"passed": 0, "total": 0, "latency_sum_ms": 0, "tokens_sum": 0, "cost_sum_usd": 0.0}
    }
    
    modes = ["pure_llm", "top1_similarity", "cass_orchestrator"]
    
    for tc_dir in sorted(tc_dirs):
        tc_id = os.path.basename(tc_dir)
        print("\n" + "="*80)
        print(f"🎬 EXECUTING TESTCASE: {tc_id}")
        print("="*80)
        
        # Load JSON configurations
        with open(os.path.join(tc_dir, "testcase.json"), "r", encoding="utf-8") as f:
            tc_data = json.load(f)
        with open(os.path.join(tc_dir, "expected.json"), "r", encoding="utf-8") as f:
            expected_data = json.load(f)
            
        tc_results = {"testcase_id": tc_id, "modes": {}}
        
        for mode in modes:
            print(f"\n⚙️ Running Mode: {mode.upper()}")
            
            # Step 1: Setup clean workspace copy
            workspace_path = ws_manager.setup_workspace(
                repo_root_rel=tc_data["repo_root"],
                testcase_id=tc_id,
                mode=mode,
                run_id=run_id
            )
            
            # Step 2: Inject buggy code
            bug_injector.inject(workspace_path, tc_data["bug_injection"])
            
            # Step 3: Run Pre-Validation sanity check
            pre_valid = PreValidator.validate(
                workspace_path=workspace_path,
                bug_type=tc_data["bug_type"],
                build_cmd=tc_data["build_command"],
                val_cmd=tc_data["validation_command"]
            )
            
            if not pre_valid:
                print(f"⚠️ [PRE-VALIDATE FAIL] Bug injection failed to behave as expected. Skipping mode {mode} for {tc_id}.")
                ws_manager.destroy_workspace(workspace_path)
                continue
                
            # Initialize isolated Skill Client for execution
            skill_client = SkillExecutionClient(workspace_path=workspace_path)
            
            # Step 4: Run Agent Execution based on mode
            metrics = {}
            if mode == "pure_llm":
                metrics = await run_baseline_a(workspace_path, tc_data, llm_client)
            elif mode == "top1_similarity":
                metrics = await run_baseline_b(workspace_path, tc_data, llm_client, skill_client)
            elif mode == "cass_orchestrator":
                metrics = await run_cass_orchestrator(workspace_path, tc_data, llm_client, skill_client)
                
            # Step 5: Post-execution Validation check
            passed, validation_err = verify_solution(workspace_path, expected_data)
            
            metrics["passed"] = passed
            if not passed:
                metrics["failure_category"] = validation_err if validation_err != "NONE" else "TEST_FAILURE"
                
            print(f"📊 Result for {mode.upper()}: {'✅ PASSED' if passed else '❌ FAILED'} | Latency: {metrics['latency_ms']}ms | Cost: ${metrics['cost_usd']:.5f}")
            
            # Accumulate metrics
            summary_metrics[mode]["total"] += 1
            if passed:
                summary_metrics[mode]["passed"] += 1
            summary_metrics[mode]["latency_sum_ms"] += metrics["latency_ms"]
            summary_metrics[mode]["tokens_sum"] += metrics["total_tokens"]
            summary_metrics[mode]["cost_sum_usd"] += metrics["cost_usd"]
            
            tc_results["modes"][mode] = metrics
            
            # Step 6: Cleanup workspace
            ws_manager.destroy_workspace(workspace_path)
            
        results_detail.append(tc_results)
        
    # Compile summary results
    final_summary = {
        "total_testcases": len(results_detail),
        "completed_testcases": len(results_detail),
        "modes": {}
    }
    
    for mode in modes:
        total = summary_metrics[mode]["total"]
        passed = summary_metrics[mode]["passed"]
        pass_rate = passed / total if total > 0 else 0.0
        avg_latency = summary_metrics[mode]["latency_sum_ms"] / total if total > 0 else 0.0
        
        final_summary["modes"][mode] = {
            "pass_rate": pass_rate,
            "avg_latency_ms": int(avg_latency),
            "total_cost_usd": summary_metrics[mode]["cost_sum_usd"],
            "total_tokens": summary_metrics[mode]["tokens_sum"]
        }
        
    benchmark_report = {
        "run_id": f"run_{run_id}",
        "timestamp": timestamp_str,
        "summary": final_summary,
        "details": results_detail
    }
    
    # Export results files (CHANGE REQUEST 4)
    results_dir = os.path.join(os.path.dirname(__file__), "benchmark_results", f"run_{run_id}")
    os.makedirs(results_dir, exist_ok=True)
    
    # Write unified report
    with open(os.path.join(results_dir, "benchmark_results.json"), "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, ensure_ascii=False, indent=2)
        
    # Write details per mode
    for mode in modes:
        mode_details = []
        for det in results_detail:
            if mode in det["modes"]:
                mode_details.append({
                    "testcase_id": det["testcase_id"],
                    "metrics": det["modes"][mode]
                })
        with open(os.path.join(results_dir, f"{mode}_details.json"), "w", encoding="utf-8") as f:
            json.dump(mode_details, f, ensure_ascii=False, indent=2)
            
    # Write summary
    with open(os.path.join(results_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=2)
        
    # Write run configuration
    run_config = {
        "run_id": f"run_{run_id}",
        "timestamp": timestamp_str,
        "llm_model": os.getenv("LLM_MODEL_NAME", "gpt-4o-mini"),
        "temperature": 0.1
    }
    with open(os.path.join(results_dir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(run_config, f, ensure_ascii=False, indent=2)
        
    print("\n" + "="*80)
    print("📊 FINAL BENCHMARK SUMMARY REPORT")
    print("="*80)
    for mode in modes:
        sm = final_summary["modes"][mode]
        print(f"- Mode {mode.upper()}: Pass Rate: {sm['pass_rate']*100:.1f}% | Avg Latency: {sm['avg_latency_ms']}ms | Cost: ${sm['total_cost_usd']:.5f} | Tokens: {sm['total_tokens']}")
    print("="*80)
    print(f"💾 Results exported to: {results_dir}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
