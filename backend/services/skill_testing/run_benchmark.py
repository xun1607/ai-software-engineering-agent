import sys
import os

# Add backend folder to sys.path to resolve imports cleanly
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import json
import time
import glob
import asyncio
import subprocess
from sentence_transformers import util

from shared.db import get_session
from services.skill_testing.models import AgentExecutionLog, init_local_db
from services.skill_testing.orchestrator import get_compiled_workflow, api_key, semantic_registry
from services.skill_testing.core.skill_client import SkillExecutionClient
from services.skill_testing.core.llm_client import OpenAIClient

# Config paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "dataset_split.json")
TESTCASES_PATH = os.path.join(BASE_DIR, "testcases.json")

def get_similarity(text1, text2):
    t1 = " ".join(text1.split())
    t2 = " ".join(text2.split())
    emb1 = semantic_registry.model.encode(t1, convert_to_tensor=True)
    emb2 = semantic_registry.model.encode(t2, convert_to_tensor=True)
    sim = float(util.cos_sim(emb1, emb2)[0][0])
    return max(0.0, min(1.0, sim))

async def main():
    print("[INFO] [BENCHMARK RUNNER] Starting benchmark runner...")
    init_local_db()
    
    # 1. Read dataset split
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Dataset split config not found at: {CONFIG_PATH}")
        return
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        split = json.load(f)
    test_ids = split.get("test", [])
    print(f"[INFO] Test split contains {len(test_ids)} tasks: {test_ids}")
    
    # 2. Read master testcases
    if not os.path.exists(TESTCASES_PATH):
        print(f"[ERROR] Testcases file not found at: {TESTCASES_PATH}")
        return
    with open(TESTCASES_PATH, "r", encoding="utf-8") as f:
        all_testcases = json.load(f)
        
    testcases = [tc for tc in all_testcases if tc.get("task_id") in test_ids]
    print(f"[INFO] Matched {len(testcases)} testcase objects from testcases.json.")
    
    # Quick Test limit (uncomment to test only the first 3 tasks)
    testcases = testcases[:3]
    
    # 3. Setup registry index
    from services.skill_testing.server import get_cached_skills
    tools_data = await get_cached_skills()
    semantic_registry.build_index(tools_data)
    
    client = SkillExecutionClient()
    workspace_dir = client.workspace_dir
    java_src_dir = client.java_src_dir
    
    baselines = ["B2", "B3"]
    results_summary = []
    
    for tc in testcases:
        tc_id = tc["task_id"]
        task_type = tc["task_type"]
        filename = tc["filename"]
        
        input_data = tc.get("input_data", {})
        code_content = input_data.get("source_code", "")
        stacktrace = tc.get("stacktrace", "")
        message = input_data.get("bug_report", "")
        
        for baseline in baselines:
            print("\n" + "="*80)
            print(f"[RUNNING] Task: {tc_id} ({task_type}) | Baseline: {baseline}")
            print("="*80)
            
            # Clean workspace
            old_files = glob.glob(os.path.join(java_src_dir, "*.java")) + glob.glob(os.path.join(workspace_dir, "*.py"))
            for fpath in old_files:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
            
            # Write code to workspace
            target_file_path = client.setup_initial_workspace(code_content, filename)
            
            # Create state
            initial_state = {
                "user_context": {
                    "code": code_content,
                    "filename": filename,
                    "stacktrace": stacktrace,
                    "message": message,
                    "task_id": tc_id,
                    "task_type": task_type,
                    "baseline_mode": baseline
                },
                "plan": [],
                "current_step_idx": 0,
                "step_count": 0,
                "history": []
            }
            
            llm_client = OpenAIClient(api_key=api_key)
            compiled_app = get_compiled_workflow(llm_client, client)
            
            tc_start_time = time.time()
            final_output = None
            try:
                final_output = await compiled_app.ainvoke(initial_state)
            except Exception as e:
                print(f"[ERROR] Workflow crash during run: {e}")
                
            elapsed_time = time.time() - tc_start_time
            print(f"[INFO] Workflow execution finished in {elapsed_time:.2f}s")
            
            # --- PHYSICAL VERIFICATION & QUALITY RATING ---
            success = False
            quality = 0.0
            
            is_finished = final_output.get("is_finished", False) if final_output else False
            final_answer = final_output.get("final_answer", "") if final_output else ""
            
            ground_truth = tc.get("ground_truth_output", {})
            
            if "patched_code" in ground_truth:
                gt_code = ground_truth["patched_code"]
                
                if os.path.exists(target_file_path) and os.path.getsize(target_file_path) > 0:
                    with open(target_file_path, "r", encoding="utf-8") as f:
                        written_code = f.read()
                    
                    similarity = get_similarity(written_code, gt_code)
                    
                    # Compile check
                    compiled_ok = False
                    if filename.endswith(".java"):
                        java_files = glob.glob(os.path.join(client.java_src_dir, "*.java"))
                        rel_paths = [os.path.relpath(p, client.workspace_dir) for p in java_files]
                        comp_res = subprocess.run(
                            ["javac"] + rel_paths,
                            cwd=client.workspace_dir,
                            capture_output=True,
                            text=True
                        )
                        compiled_ok = (comp_res.returncode == 0)
                        if not compiled_ok:
                            print(f"[WARNING] Javac compile failed:\n{comp_res.stderr}")
                    elif filename.endswith(".py"):
                        comp_res = subprocess.run(
                            [sys.executable, "-m", "py_compile", filename],
                            cwd=client.workspace_dir,
                            capture_output=True,
                            text=True
                        )
                        compiled_ok = (comp_res.returncode == 0)
                        if not compiled_ok:
                            print(f"[WARNING] Python syntax check failed:\n{comp_res.stderr}")
                    
                    if compiled_ok:
                        success = True
                        quality = similarity
                    else:
                        if similarity >= 0.8:
                            success = True
                            quality = similarity
                        else:
                            success = False
                            quality = 0.0
                else:
                    print(f"[ERROR] Output file not found at: {target_file_path}")
                    success = False
                    quality = 0.0
            else:
                # Text-based tasks (explanation / review)
                gt_text = ground_truth.get("explanation") or ground_truth.get("review_notes") or ""
                if final_answer and gt_text:
                    similarity = get_similarity(final_answer, gt_text)
                    quality = similarity
                    success = (similarity >= 0.6)
                else:
                    success = False
                    quality = 0.0
            
            print(f"[EVALUATION] Success={success} | Quality={quality:.4f}")
            
            # 4. Save results to database
            try:
                with get_session() as session:
                    from sqlalchemy import update
                    stmt = (
                        update(AgentExecutionLog)
                        .where(AgentExecutionLog.task_id == tc_id)
                        .where(AgentExecutionLog.baseline_mode == baseline)
                        .values(success=success, quality=quality)
                    )
                    session.execute(stmt)
                print(f"[DB UPDATE] Successfully saved metrics to SQLite.")
            except Exception as db_err:
                print(f"[DB UPDATE ERROR] Failed to save execution metrics: {db_err}")
                
            results_summary.append({
                "task_id": tc_id,
                "baseline": baseline,
                "success": success,
                "quality": quality,
                "time": f"{elapsed_time:.2f}s"
            })
            
    print("\n" + "="*80)
    print("BENCHMARK RUN COMPLETED!")
    print("="*80)
    for r in results_summary:
        print(f"Task: {r['task_id']} | Baseline: {r['baseline']} | Success: {r['success']} | Quality: {r['quality']:.4f} | Time: {r['time']}")

if __name__ == "__main__":
    asyncio.run(main())
