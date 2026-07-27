import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import csv
import shutil
import argparse
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Add swe_agent and service root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "swe_agent")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import HumanMessage

# Core Architecture Imports
from swe_agent.core.brain import OpenAIBrain
from swe_agent.core.sandbox import LocalSandbox
from swe_agent.factory import create_swe_agent
from swe_agent.skills.markdown_skill import DynamicMarkdownSkill
from swe_agent.skills.registry import SkillRegistry
from swe_agent.tools import (
    ReadFileTool, WriteFileTool, EditFileTool, ListFilesTool,
    FindFileTool, SearchCodeTool, TerminalShellTool, RunTestsTool,
    CompileProjectTool, GitDiffTool
)
from swe_agent.cass_bridge import CASSBridge

# Separate SRP Modules
from legacy_skills import LegacySuggestFixSkill, LegacyReadContextSkill
from visualizer import BenchmarkVisualizer
from testcases_suite import get_testcases

def seed_reputation_db(db_manager):
    """
    Seed reputation metrics via DBManager abstraction (update_metrics).
    """
    for _ in range(30):
        db_manager.update_metrics("suggest_python_fix", latency_ms=120.0, cost=0.0, success=True)
    for _ in range(25):
        db_manager.update_metrics("read_code_context", latency_ms=100.0, cost=0.0, success=True)
    for _ in range(5):
        db_manager.update_metrics("python-pytest-runner", latency_ms=300.0, cost=0.0, success=True)
    for _ in range(10):
        db_manager.update_metrics("java-oom-analyzer", latency_ms=450.0, cost=0.0, success=False)

def remove_readonly(func, path, exc_info):
    """Clear read-only attribute on Windows git pack files and retry deletion."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

def log_cass_decision(log_path: str, tc_id: str, query: str, cass_details: dict):
    """
    Log CASS selection details returned directly by CASSBridge / CASS pipeline.
    """
    context = cass_details.get("context", {})
    host_os = context.get("environment", {}).get("os_name", "unknown")
    dropped_skills = cass_details.get("dropped_skills", [])
    selected_skills = cass_details.get("selected_skills", [])
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')} | Testcase ID: {tc_id}\n")
        f.write(f"Task query: '{query}'\n")
        f.write(f"Current Host OS: {host_os}\n")
        f.write("-" * 40 + "\n")
        f.write("Step 1: Constraint Filter Pipeline (CASS Diagnostics)\n")
        
        if dropped_skills:
            for s in dropped_skills:
                f.write(f"  [DROPPED] Skill '{s.name}' dropped by CASS (Constraints: {s.constraints})\n")
        else:
            f.write("  No skills dropped by constraint filter.\n")
                
        f.write(f"\nStep 2: Semantic Filter & Reputation Ranking (Top-{len(selected_skills)})\n")
        for idx, s in enumerate(selected_skills, 1):
            f.write(f"  {idx}. Selected: '{s.name}' | Desc: {s.description[:70]}...\n")
        f.write("=" * 60 + "\n\n")

def run_benchmark(
    selected_ids: Optional[List[str]] = None,
    category: Optional[str] = None,
    runs_per_tc: int = 1
):
    print("🚀 Starting CASS Benchmark Runner...")
    db_path = "benchmark_cass.db"
    log_path = "cass_selection.log"
    csv_file = "benchmark_results.csv"
    chart_file = "benchmark_comparison.png"
    
    # Reset DB & initialize CASS Bridge
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(log_path):
        os.remove(log_path)
        
    cass_bridge = CASSBridge(db_path)
    seed_reputation_db(cass_bridge.cass.db_manager)
    
    # Prepare SkillRegistry
    registry = SkillRegistry()
    brain = OpenAIBrain(model_name="gpt-4o")
    tools = [
        ReadFileTool(), WriteFileTool(), EditFileTool(), ListFilesTool(),
        FindFileTool(), SearchCodeTool(), TerminalShellTool(), RunTestsTool(),
        CompileProjectTool(), GitDiffTool()
    ]
    
    # 1. Load generated skills via DynamicMarkdownSkill
    skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "skills"))
    if os.path.exists(skills_dir):
        for folder in os.listdir(skills_dir):
            folder_path = os.path.join(skills_dir, folder)
            if os.path.isdir(folder_path):
                md_path = os.path.join(folder_path, "SKILL.md")
                if os.path.exists(md_path):
                    skill = DynamicMarkdownSkill(md_path, brain, tools)
                    registry.register(skill)
                    
    # 2. Register legacy skills
    registry.register(LegacySuggestFixSkill())
    registry.register(LegacyReadContextSkill())
    
    all_skills = registry.get_all_skills()
    print(f"Registered skills in SkillRegistry: {len(all_skills)}")
    
    # Load filtered Testcases
    testcases = get_testcases(selected_ids, category)
    print(f"Selected Testcases ({len(testcases)} total): {[tc['id'] for tc in testcases]}")
    
    results = []
    if os.path.exists(csv_file):
        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append({
                        "Testcase_ID": row["Testcase_ID"],
                        "Scenario": row["Scenario"],
                        "Total Skills Bound": int(row["Total Skills Bound"]) if row["Total Skills Bound"] else 0,
                        "Prompt Tokens": int(row["Prompt Tokens"]) if row["Prompt Tokens"] else 0,
                        "Completion Tokens": int(row["Completion Tokens"]) if row["Completion Tokens"] else 0,
                        "Total Tokens": int(row["Total Tokens"]) if row["Total Tokens"] else 0,
                        "Cost": float(row["Cost"]) if row["Cost"] else 0.0,
                        "Latency (ms)": float(row["Latency (ms)"]) if row["Latency (ms)"] else 0.0,
                        "Success": int(row["Success"]) if row["Success"] else 0
                    })
            print(f"Loaded {len(results)} existing benchmark run logs from {csv_file}")
        except Exception as ex:
            print(f"Note: Starting fresh benchmark results ({ex})")
    
    for tc in testcases:
        tc_id = tc["id"]
        tc_name = tc["name"]
        task_desc = tc["task_desc"]
        initial_files = tc.get("files", {})
        test_cmd = tc.get("test_cmd", "")
        
        print(f"\n==========================================")
        print(f"📌 Running Testcase: {tc_id} ({tc_name})")
        print(f"==========================================")
        
        for run_idx in range(1, runs_per_tc + 1):
            if runs_per_tc > 1:
                print(f"--- Iteration {run_idx}/{runs_per_tc} ---")
                
            # SCENARIO A: BASELINE
            workspace_a = f"./workspace_baseline_{tc_id}"
            if os.path.exists(workspace_a):
                shutil.rmtree(workspace_a, onerror=remove_readonly)
            sandbox_a = LocalSandbox(workspace_a)
            
            # Seed initial testcase files into sandbox
            repo_dir = tc.get("repo_dir")
            if repo_dir and os.path.exists(os.path.abspath(repo_dir)):
                shutil.copytree(os.path.abspath(repo_dir), sandbox_a.workspace_path, dirs_exist_ok=True)
            for filepath, content in initial_files.items():
                sandbox_a.write_file(filepath, content)
                
            agent_a = create_swe_agent(brain, sandbox_a, all_skills, cass_bridge=None)
            
            initial_state_a = {
                "messages": [HumanMessage(content=task_desc)],
                "iteration_count": 0,
                "is_valid": False,
                "feedback": None,
                "test_command": test_cmd
            }
            
            start_time = time.time()
            with get_openai_callback() as cb_a:
                try:
                    final_state_a = agent_a.invoke(initial_state_a, {"recursion_limit": 15})
                    success_a = final_state_a.get("is_valid", False)
                except Exception as e:
                    print(f"Scenario A ({tc_id}) Failed: {e}")
                    success_a = False
                    
            latency_a = (time.time() - start_time) * 1000
            print(f"Baseline ({tc_id}) -> Success: {success_a} | Tokens: {cb_a.total_tokens} | Latency: {latency_a:.2f}ms")
            
            results.append({
                "Testcase_ID": tc_id,
                "Scenario": "Baseline",
                "Total Skills Bound": len(all_skills),
                "Prompt Tokens": cb_a.prompt_tokens,
                "Completion Tokens": cb_a.completion_tokens,
                "Total Tokens": cb_a.total_tokens,
                "Cost": cb_a.total_cost,
                "Latency (ms)": latency_a,
                "Success": 1 if success_a else 0
            })
            
            # SCENARIO B: CASS-ENABLED
            workspace_b = f"./workspace_cass_{tc_id}"
            if os.path.exists(workspace_b):
                shutil.rmtree(workspace_b, onerror=remove_readonly)
            sandbox_b = LocalSandbox(workspace_b)
            
            if repo_dir and os.path.exists(os.path.abspath(repo_dir)):
                shutil.copytree(os.path.abspath(repo_dir), sandbox_b.workspace_path, dirs_exist_ok=True)
            for filepath, content in initial_files.items():
                sandbox_b.write_file(filepath, content)
                
            session_id = f"session_{tc_id}_run{run_idx}"
            cass_details = cass_bridge.get_optimized_skills_with_details(all_skills, session_id, task_desc, top_k=3)
            log_cass_decision(log_path, tc_id, task_desc, cass_details)
            
            agent_b = create_swe_agent(brain, sandbox_b, all_skills, cass_bridge=cass_bridge)
            
            initial_state_b = {
                "messages": [HumanMessage(content=task_desc)],
                "iteration_count": 0,
                "is_valid": False,
                "feedback": None,
                "session_id": session_id,
                "test_command": test_cmd
            }
            
            start_time = time.time()
            with get_openai_callback() as cb_b:
                try:
                    final_state_b = agent_b.invoke(initial_state_b, {"recursion_limit": 15})
                    success_b = final_state_b.get("is_valid", False)
                except Exception as e:
                    print(f"Scenario B ({tc_id}) Failed: {e}")
                    success_b = False
                    
            latency_b = (time.time() - start_time) * 1000
            print(f"CASS ({tc_id}) -> Success: {success_b} | Tokens: {cb_b.total_tokens} | Latency: {latency_b:.2f}ms")
            
            results.append({
                "Testcase_ID": tc_id,
                "Scenario": "CASS-Enabled",
                "Total Skills Bound": 3,
                "Prompt Tokens": cb_b.prompt_tokens,
                "Completion Tokens": cb_b.completion_tokens,
                "Total Tokens": cb_b.total_tokens,
                "Cost": cb_b.total_cost,
                "Latency (ms)": latency_b,
                "Success": 1 if success_b else 0
            })
            
            # Clean up temporary test workspaces
            for ws in [workspace_a, workspace_b]:
                if os.path.exists(ws):
                    shutil.rmtree(ws, onerror=remove_readonly)

    # Save aggregated CSV
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\n📈 Benchmark results saved to {csv_file}")
    
    # Plot using visualizer module
    # Calculate average across scenarios for chart plotting
    scenarios_summary = []
    for sc in ["Baseline", "CASS-Enabled"]:
        sc_rows = [r for r in results if r["Scenario"] == sc]
        if sc_rows:
            avg_prompt = sum(r["Prompt Tokens"] for r in sc_rows) / len(sc_rows)
            avg_total = sum(r["Total Tokens"] for r in sc_rows) / len(sc_rows)
            avg_latency = sum(r["Latency (ms)"] for r in sc_rows) / len(sc_rows)
            scenarios_summary.append({
                "Scenario": sc,
                "Prompt Tokens": avg_prompt,
                "Total Tokens": avg_total,
                "Latency (ms)": avg_latency
            })
            
    BenchmarkVisualizer.plot_comparison(scenarios_summary, chart_file)
    print(f"📊 Chart comparison generated: {chart_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CASS vs Baseline Benchmark Runner")
    parser.add_argument("--tc", "--testcase", nargs="+", help="Specific Testcase IDs to run (e.g. tc_python_syntax tc_java_npe)")
    parser.add_argument("--category", type=str, help="Filter testcases by category (e.g. python, java, git, system)")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per testcase (default: 1)")
    args = parser.parse_args()
    
    run_benchmark(selected_ids=args.tc, category=args.category, runs_per_tc=args.runs)
