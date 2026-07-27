import os
import sys
import json
import subprocess
import shutil
import ast
from pathlib import Path
from datasets import load_dataset

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

SWE_REPOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "benchmark_repos", "swe_repos"))
os.makedirs(SWE_REPOS_DIR, exist_ok=True)

def remove_readonly(func, path, exc_info):
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

def convert_swe_to_cass_testcase(swe_item: dict) -> dict:
    """
    Step 2: Converter from SWE-bench Lite record schema to CASS Testcase Schema
    """
    instance_id = swe_item['instance_id']
    repo_full_name = swe_item['repo']
    repo_folder = instance_id.replace("/", "__").replace("-", "_")
    
    problem_statement = swe_item.get('problem_statement', '')
    task_desc = (
        f"SWE-bench Lite Real-World Task [{instance_id}]:\n\n"
        f"{problem_statement}\n\n"
        f"Yêu cầu: Hãy phân tích issue mô tả ở trên, kiểm tra mã nguồn repository, sửa lỗi và đảm bảo toàn bộ unit test PASS."
    )
    
    fail_to_pass_raw = swe_item.get('FAIL_TO_PASS', [])
    if isinstance(fail_to_pass_raw, str):
        try:
            fail_to_pass_list = ast.literal_eval(fail_to_pass_raw)
        except Exception:
            fail_to_pass_list = [fail_to_pass_raw]
    else:
        fail_to_pass_list = fail_to_pass_raw
        
    test_targets = []
    if isinstance(fail_to_pass_list, list):
        for t in fail_to_pass_list:
            clean_t = str(t).split("::")[0]
            if clean_t not in test_targets:
                test_targets.append(clean_t)
            
    test_files_str = " ".join(test_targets) if test_targets else "tests/"
    test_cmd = f"python -m pytest {test_files_str}"
    
    clean_id = f"tc_swe_{instance_id.replace('-', '_')}"
    
    return {
        "id": clean_id,
        "name": f"SWE-bench Lite: {instance_id}",
        "category": "python",
        "repo_dir": f"benchmark_repos/swe_repos/{repo_folder}",
        "task_desc": task_desc,
        "test_cmd": test_cmd,
        "base_commit": swe_item['base_commit'],
        "repo_url": f"https://github.com/{repo_full_name}",
        "test_patch": swe_item.get('test_patch', '')
    }

def setup_swe_buggy_environment(tc: dict):
    """
    Step 3: Automatically Recreate Bug Environment (Clone, Checkout Base Commit, Apply Test Patch)
    """
    repo_url = tc["repo_url"]
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), tc["repo_dir"]))
    base_commit = tc["base_commit"]
    test_patch = tc.get("test_patch", "")
    
    print(f"\nSetting up SWE-bench Environment for: {tc['name']}")
    
    # 1. Clone repository with depth 1 or shallow if possible, or standard git clone
    if not os.path.exists(repo_dir):
        print(f"  [1/3] Cloning {repo_url} into {repo_dir}...")
        subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
    else:
        print(f"  [1/3] Repo directory already exists at {repo_dir}")
        
    # 2. Checkout base_commit to recreate exact buggy state
    print(f"  [2/3] Checking out base_commit: {base_commit}...")
    subprocess.run(["git", "reset", "--hard"], cwd=repo_dir, check=True)
    subprocess.run(["git", "checkout", base_commit], cwd=repo_dir, check=True)
    
    # 3. Apply test_patch (validation tests written by SWE-bench authors)
    if test_patch:
        print("  [3/3] Applying test_patch verification tests...")
        patch_file = os.path.join(repo_dir, "swe_test.patch")
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(test_patch)
        try:
            subprocess.run(["git", "apply", "swe_test.patch"], cwd=repo_dir, check=True)
            print("  [OK] test_patch applied successfully!")
        except Exception as patch_err:
            print(f"  [WARN] Warning applying git patch: {patch_err}")
            
    print(f"[SUCCESS] Bug environment successfully recreated for {tc['id']}!")

if __name__ == "__main__":
    print("=========================================================")
    print("SWE-bench Lite Extractor & Environment Setup Tool")
    print("=========================================================")
    
    print("\n[Step 1] Loading SWE-bench Lite dataset from Hugging Face...")
    dataset = load_dataset("SWE-bench/SWE-bench_Lite", split="test")
    print(f"  [OK] Total instances in SWE-bench Lite: {len(dataset)}")
    
    # Select lightweight, famous repos: pallets/flask, psf/requests, pytest-dev/pytest
    target_repos = ["pallets/flask", "psf/requests", "pytest-dev/pytest"]
    selected_items = []
    
    for item in dataset:
        if item["repo"] in target_repos and item["repo"] not in [x["repo"] for x in selected_items]:
            selected_items.append(item)
            if len(selected_items) >= 3:
                break
                
    if not selected_items:
        selected_items = [dataset[i] for i in range(3)]
        
    print(f"\n[Step 2] Converting {len(selected_items)} SWE-bench Lite records to CASS Testcase Schema...")
    cass_testcases = []
    for item in selected_items:
        tc = convert_swe_to_cass_testcase(item)
        cass_testcases.append(tc)
        print(f"  • Extracted Testcase: ID='{tc['id']}' | Repo='{item['repo']}'")
        
    print("\n[Step 3] Recreating Bug Environments (Git Clone, Base Commit Checkout, Apply Patch)...")
    for tc in cass_testcases:
        try:
            setup_swe_buggy_environment(tc)
        except Exception as e:
            print(f"  [ERROR] Error setting up {tc['id']}: {e}")
            
    output_json = os.path.abspath(os.path.join(os.path.dirname(__file__), "swe_lite_testcases.json"))
    suite_export = [{k: v for k, v in tc.items() if k != "test_patch"} for tc in cass_testcases]
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(suite_export, f, indent=2, ensure_ascii=False)
        
    print(f"\n[SAVED] Saved extracted testcase metadata to: {output_json}")
    print("=========================================================")
    print("SWE-bench Lite extraction & environment setup complete!")