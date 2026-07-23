import os
import sys
import time
import csv
import shutil
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Add swe_agent and service root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "swe_agent")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import HumanMessage

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

from legacy_skills import LegacySuggestFixSkill, LegacyReadContextSkill
from visualizer import BenchmarkVisualizer

def seed_reputation_db(db_manager):
    """
    Seed reputation metrics via DBManager abstraction (update_metrics)
    """
    # Seed high success counts (alpha) for core skills
    for _ in range(30):
        db_manager.update_metrics("suggest_python_fix", latency_ms=120.0, cost=0.0, success=True)
    for _ in range(25):
        db_manager.update_metrics("read_code_context", latency_ms=100.0, cost=0.0, success=True)
        
    # Seed mixed success/failure for secondary skills
    for _ in range(5):
        db_manager.update_metrics("python-pytest-runner", latency_ms=300.0, cost=0.0, success=True)
    for _ in range(10):
        db_manager.update_metrics("java-oom-analyzer", latency_ms=450.0, cost=0.0, success=False)

def log_cass_decision(log_path: str, query: str, cass_details: dict):
    """
    Log CASS selection details returned directly by CASSBridge / CASS pipeline.
    """
    context = cass_details.get("context", {})
    host_os = context.get("environment", {}).get("os_name", "unknown")
    dropped_skills = cass_details.get("dropped_skills", [])
    selected_skills = cass_details.get("selected_skills", [])
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
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
        f.write("=" * 60 + "\n")

def run_benchmark():
    print("🚀 Starting Refactored CASS vs Baseline Benchmark...")
    db_path = "benchmark_cass.db"
    log_path = "cass_selection.log"
    csv_file = "benchmark_results.csv"
    chart_file = "benchmark_comparison.png"
    
    # Reset DB & initialize CASS Bridge
    if os.path.exists(db_path):
        os.remove(db_path)
        
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
    
    # 1. Load generated skills via DynamicMarkdownSkill into Registry
    skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "skills"))
    if os.path.exists(skills_dir):
        for folder in os.listdir(skills_dir):
            folder_path = os.path.join(skills_dir, folder)
            if os.path.isdir(folder_path):
                md_path = os.path.join(folder_path, "SKILL.md")
                if os.path.exists(md_path):
                    skill = DynamicMarkdownSkill(md_path, brain, tools)
                    registry.register(skill)
                    
    # 2. Register legacy skills into Registry
    registry.register(LegacySuggestFixSkill())
    registry.register(LegacyReadContextSkill())
    
    all_skills = registry.get_all_skills()
    print(f"Registered skills in SkillRegistry: {len(all_skills)}")
    
    # Define test task
    task_desc = (
        "Hãy tạo file 'buggy.py' in ra chuỗi 'Fixed!'. "
        "BẮT BUỘC: Ở lần đầu tiên, hãy viết thiếu dấu ngoặc đóng ')' để tôi test tính năng sửa lỗi của hệ thống."
    )
    
    results = []
    
    # ==========================================
    # SCENARIO A: BASELINE (All Skills Bound)
    # ==========================================
    print("\n--- Running Scenario A: Baseline (All Skills Bound) ---")
    workspace_a = "./workspace_baseline"
    if os.path.exists(workspace_a):
        shutil.rmtree(workspace_a)
    sandbox_a = LocalSandbox(workspace_a)
    
    # Factory Injection with cass_bridge=None for Baseline
    agent_a = create_swe_agent(brain, sandbox_a, all_skills, cass_bridge=None)
    
    initial_state_a = {
        "messages": [HumanMessage(content=task_desc)],
        "iteration_count": 0,
        "is_valid": False,
        "feedback": None
    }
    
    start_time = time.time()
    with get_openai_callback() as cb_a:
        try:
            final_state_a = agent_a.invoke(initial_state_a, {"recursion_limit": 15})
            success_a = final_state_a.get("is_valid", False)
        except Exception as e:
            print(f"Scenario A Failed with exception: {e}")
            success_a = False
            
    latency_a = (time.time() - start_time) * 1000
    print(f"Baseline Results -> Success: {success_a} | Tokens: {cb_a.total_tokens} | Latency: {latency_a:.2f}ms | Cost: ${cb_a.total_cost:.5f}")
    
    results.append({
        "Scenario": "Baseline",
        "Total Skills Bound": len(all_skills),
        "Prompt Tokens": cb_a.prompt_tokens,
        "Completion Tokens": cb_a.completion_tokens,
        "Total Tokens": cb_a.total_tokens,
        "Cost": cb_a.total_cost,
        "Latency (ms)": latency_a,
        "Success": 1 if success_a else 0
    })
    
    # ==========================================
    # SCENARIO B: CASS-ENABLED (Top-3 Bound)
    # ==========================================
    print("\n--- Running Scenario B: CASS-Enabled (Top-3 Bound) ---")
    workspace_b = "./workspace_cass"
    if os.path.exists(workspace_b):
        shutil.rmtree(workspace_b)
    sandbox_b = LocalSandbox(workspace_b)
    
    session_id = "session_bench_refactored"
    
    # Log CASS decision details from CASSBridge diagnostic API
    cass_details = cass_bridge.get_optimized_skills_with_details(all_skills, session_id, task_desc, top_k=3)
    log_cass_decision(log_path, task_desc, cass_details)
    
    # Factory Injection with cass_bridge for CASS Scenario
    agent_b = create_swe_agent(brain, sandbox_b, all_skills, cass_bridge=cass_bridge)
    
    initial_state_b = {
        "messages": [HumanMessage(content=task_desc)],
        "iteration_count": 0,
        "is_valid": False,
        "feedback": None,
        "session_id": session_id
    }
    
    start_time = time.time()
    with get_openai_callback() as cb_b:
        try:
            final_state_b = agent_b.invoke(initial_state_b, {"recursion_limit": 15})
            success_b = final_state_b.get("is_valid", False)
        except Exception as e:
            print(f"Scenario B Failed with exception: {e}")
            success_b = False
            
    latency_b = (time.time() - start_time) * 1000
    print(f"CASS Results -> Success: {success_b} | Tokens: {cb_b.total_tokens} | Latency: {latency_b:.2f}ms | Cost: ${cb_b.total_cost:.5f}")
    
    results.append({
        "Scenario": "CASS-Enabled",
        "Total Skills Bound": 3,
        "Prompt Tokens": cb_b.prompt_tokens,
        "Completion Tokens": cb_b.completion_tokens,
        "Total Tokens": cb_b.total_tokens,
        "Cost": cb_b.total_cost,
        "Latency (ms)": latency_b,
        "Success": 1 if success_b else 0
    })
    
    # Clean up workspace folders
    for ws in [workspace_a, workspace_b]:
        if os.path.exists(ws):
            shutil.rmtree(ws)
            
    # Output CSV
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\n📈 Results saved to {csv_file}")
    
    # Plot using visualizer module
    BenchmarkVisualizer.plot_comparison(results, chart_file)
    print(f"📊 Chart comparison generated: {chart_file}")

if __name__ == "__main__":
    run_benchmark()
