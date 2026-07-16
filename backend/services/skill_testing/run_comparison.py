import os
import json
import asyncio
import time
import re
from typing import List, Dict, Any

from services.skill_testing.benchmark_runner import WorkspaceManager
from services.skill_testing.core.skill_client import SkillExecutionClient
from services.skill_testing.core.llm_client import OpenAIClient
from services.skill_testing.orchestrator import run_pipeline, api_key

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TESTCASES_JSON_PATH = os.path.join(BACKEND_DIR, "services", "skill_testing", "testcases.json")
RESULTS_DIR = os.path.join(BACKEND_DIR, "services", "skill_testing", "benchmark_results")

class BenchmarkSkillExecutionClient(SkillExecutionClient):
    """Subclass to mock compilation/runtime executions for snippet-only testcases."""
    async def execute_skill(self, skill_name: str, args: dict) -> dict:
        name_clean = skill_name.lower().replace("-", "_")
        
        # Mock compilation and execution checks for standalone snippet files
        if name_clean in ["debug_java_null_pointer", "debug_python_error"]:
            print(f"🎮 [MOCK RUNTIME] Giả lập chạy thành công cho kỹ năng '{skill_name}' trên file snippet.")
            return {
                "status": "SUCCESS",
                "stdout": "Compiled/Executed successfully (Mocked for snippet).",
                "stderr": "",
                "returncode": 0,
                "message": "✅ [SKILL LOG] Mock runtime: Code executed successfully."
            }
            
        # Use execution client logic for file writing, reading, and parsing
        return await super().execute_skill(skill_name, args)

async def verify_patch_semantic(generated: str, ground_truth: str, llm_client) -> bool:
    """Verifies that the generated patch is semantically equivalent to the ground truth."""
    # 1. Exact match ignoring whitespaces
    def clean(s: str) -> str:
        return "".join(s.split())
    if clean(generated) == clean(ground_truth):
        return True
        
    # 2. Semantic evaluation via LLM
    prompt = f"""
    Compare the generated code with the ground truth code.
    Are they semantically equivalent in resolving the bug described? 
    The logic, safety checks, and corrections should be functionally identical.
    
    GENERATED CODE:
    {generated}
    
    GROUND TRUTH CODE:
    {ground_truth}
    
    INSTRUCTIONS:
    1. Return JSON with a single key "equivalent" (true or false).
    2. Output ONLY valid JSON. Do not include markdown blocks.
    """
    try:
        resp = await llm_client.call(prompt, "Verify equivalence.")
        cleaned = resp.strip()
        if "```" in cleaned:
            m = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
            if m:
                cleaned = m.group(1).strip()
        data = json.loads(cleaned)
        return data.get("equivalent", False)
    except Exception as e:
        print(f"⚠️ [VERIFIER ERROR] Lỗi khi LLM đối chứng ngữ nghĩa: {e}")
        return False

async def run_single_testcase(tc_data: dict, baseline_mode: str, run_id: int, llm_client) -> Dict[str, Any]:
    """Runs a single testcase for a given baseline mode and returns the results."""
    testcase_id = tc_data["task_id"]
    filename = tc_data["filename"]
    print(f"\n=========================================================")
    print(f"🎬 [RUN] Testcase: {testcase_id} | Chế độ: {baseline_mode} | Run ID: {run_id}")
    print(f"=========================================================")
    
    workspace_path = None
    try:
        # 1. Setup blank workspace sandbox
        workspace_path = WorkspaceManager.setup_workspace(
            repo_root=None,
            testcase_id=testcase_id,
            mode=baseline_mode,
            run_id=run_id
        )
        
        # 2. Write initial buggy source code
        initial_code = tc_data["input_data"]["source_code"]
        skill_client = BenchmarkSkillExecutionClient(workspace_path=workspace_path)
        skill_client.setup_initial_workspace(initial_code, filename)
        
        # 3. Run the Agent Pipeline passing the custom skill_client
        start_time = time.time()
        final_state = await run_pipeline(
            code_content=initial_code,
            filename=filename,
            stacktrace=tc_data["stacktrace"],
            message=tc_data["message"],
            workspace_path=workspace_path,
            baseline_mode=baseline_mode,
            skill_client=skill_client
        )
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 4. Read final patched code from workspace
        patched_file_path = skill_client.get_file_path(filename)
        if os.path.exists(patched_file_path):
            with open(patched_file_path, "r", encoding="utf-8", errors="ignore") as f:
                generated_patch = f.read()
        else:
            generated_patch = ""
            
        # 5. Dynamic Dual Validation (Environment Validator vs Ground Truth)
        last_skill = None
        history = final_state.get("history", []) if isinstance(final_state, dict) else getattr(final_state, "history", [])
        if history:
            last_skill = history[-1].get("skill")
            
        from services.skill_testing.core.validation_runtime import validation_runtime
        has_validator = last_skill in validation_runtime.validator_mapping if last_skill else False
        
        if has_validator:
            print(f"🔍 [BENCHMARK VALIDATOR] Kích hoạt ValidationRuntime cho file {filename}...")
            validation_feedback = await validation_runtime.validate(
                skill_name=last_skill,
                args={"patched_code": generated_patch, "file": filename},
                workspace_dir=skill_client.workspace_dir,
                skill_client_class_name=skill_client.__class__.__name__,
                model_client=llm_client
            )
            success = (validation_feedback.exit_code == 0) if validation_feedback else False
            verify_msg = "Validator compile thành công." if success else f"Validator compile thất bại:\n{validation_feedback.stderr if validation_feedback else 'No feedback'}"
        else:
            print(f"🔍 [BENCHMARK VALIDATOR] Kích hoạt Semantic Ground Truth Match cho file {filename}...")
            ground_truth = tc_data.get("ground_truth_output", {}).get("patched_code", "")
            success = await verify_patch_semantic(generated_patch, ground_truth, llm_client)
            verify_msg = "Bản vá tương đương ngữ nghĩa với Ground Truth." if success else "Bản vá chưa sửa đúng lỗi hoặc khác biệt ngữ nghĩa."
        
        return {
            "testcase_id": testcase_id,
            "mode": baseline_mode,
            "success": success,
            "latency_ms": latency_ms,
            "total_tokens": final_state.get("total_tokens", 0) if isinstance(final_state, dict) else getattr(final_state, "total_tokens", 0),
            "total_cost": final_state.get("total_cost", 0.0) if isinstance(final_state, dict) else getattr(final_state, "total_cost", 0.0),
            "step_count": final_state.get("step_count", 0) if isinstance(final_state, dict) else getattr(final_state, "step_count", 0),
            "message": verify_msg
        }
        
    except Exception as e:
        print(f"❌ [CRASH] Lỗi xảy ra: {e}")
        import traceback
        traceback.print_exc()
        return {
            "testcase_id": testcase_id,
            "mode": baseline_mode,
            "success": False,
            "latency_ms": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "step_count": 0,
            "message": f"Crash: {str(e)}"
        }
    finally:
        if workspace_path:
            WorkspaceManager.destroy_workspace(workspace_path)

async def run_benchmark(modes: List[str] = ["B2", "B4"]):  #"B1", "B2", "B3", 
    """Runs all testcases from testcases.json across the 4 baselines and prints comparison table."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    if not os.path.exists(TESTCASES_JSON_PATH):
        print(f"❌ File {TESTCASES_JSON_PATH} không tồn tại.")
        return
        
    with open(TESTCASES_JSON_PATH, "r", encoding="utf-8") as f:
        testcases = json.load(f)
        
    # Cap to 30 testcases as requested by the user
    testcases = testcases[:4]
    
    print(f"🔍 [BENCHMARK] Nạp thành công {len(testcases)} testcases từ testcases.json!")
    print(f"⚙️ [BENCHMARK] Chạy đối chứng trên các chế độ: {modes}")
    
    run_id = int(time.time())
    llm_client = OpenAIClient(api_key=api_key)
    all_results = []
    
    for tc in testcases:
        for mode in modes:
            result = await run_single_testcase(tc, mode, run_id, llm_client)
            all_results.append(result)
            
    # Print Console Report Table
    print("\n" + "="*80)
    print("📊 BÁO CÁO KẾT QUẢ THỰC NGHIỆM ĐỐI CHỨNG (BENCHMARK SUMMARY) 📊")
    print("="*80)
    print(f"{'Testcase ID':<12} | {'Mode':<10} | {'Success':<8} | {'Latency':<10} | {'Tokens':<10} | {'Cost (USD)':<10}")
    print("-"*80)
    
    for r in all_results:
        success_str = "PASS ✅" if r["success"] else "FAIL ❌"
        cost_str = f"${r['total_cost']:.5f}"
        print(f"{r['testcase_id']:<12} | {r['mode']:<10} | {success_str:<8} | {r['latency_ms']:<8}ms | {r['total_tokens']:<10} | {cost_str:<10}")
        
    print("="*80)
    
    output_file = os.path.join(RESULTS_DIR, f"benchmark_results_{run_id}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"💾 [BENCHMARK] Đã xuất báo cáo chi tiết ra file: '{output_file}'")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
