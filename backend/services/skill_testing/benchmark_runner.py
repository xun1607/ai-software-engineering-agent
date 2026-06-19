import os
import shutil
import subprocess
import time
import json
from typing import Dict, Any, List

from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.core.llm_client import OpenAIClient
from services.skill_testing.core.skill_client import SkillExecutionClient

class WorkspaceManager:
    """Manages the lifecycle of isolated benchmark workspaces."""
    
    def __init__(self, base_temp_dir: str = None):
        if base_temp_dir is None:
            base_temp_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "workspace_temp")
            )
        self.base_temp_dir = base_temp_dir
        os.makedirs(self.base_temp_dir, exist_ok=True)
        
    def setup_workspace(self, repo_root_rel: str, testcase_id: str, mode: str, run_id: str) -> str:
        """Copies the read-only golden repo to a temporary workspace for isolation."""
        # Find absolute path of the golden repo
        golden_repo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", repo_root_rel)
        )
        if not os.path.exists(golden_repo_path):
            golden_repo_path = os.path.abspath(repo_root_rel)
            if not os.path.exists(golden_repo_path):
                raise FileNotFoundError(f"Golden repository not found at: {golden_repo_path}")
                
        workspace_path = os.path.join(
            self.base_temp_dir, f"run_{run_id}", testcase_id, mode
        )
        
        if os.path.exists(workspace_path):
            self.destroy_workspace(workspace_path)
            
        print(f"📁 [WORKSPACE] Creating isolated copy: {golden_repo_path} -> {workspace_path}")
        
        def ignore_patterns(path, names):
            ignored = []
            for name in names:
                if name in ['.git', 'target', '.gradle', 'build', '.idea', '.vscode', 'workspace_temp']:
                    ignored.append(name)
            return ignored
            
        shutil.copytree(golden_repo_path, workspace_path, ignore=ignore_patterns)
        return workspace_path
        
    def destroy_workspace(self, workspace_path: str):
        """Clean up the temp workspace directory recursively to reclaim disk space."""
        if os.path.exists(workspace_path):
            print(f"🧹 [WORKSPACE] Destroying workspace: {workspace_path}")
            shutil.rmtree(workspace_path, ignore_errors=True)


class BugInjector:
    """Handles injecting bugs into isolated workspaces deterministically."""
    
    def inject(self, workspace_path: str, bug_injection: dict) -> str:
        target_file = bug_injection["target_file"]
        inject_type = bug_injection["inject_type"]
        original_content = bug_injection["original_content"]
        buggy_content = bug_injection["buggy_content"]
        
        file_path = os.path.join(workspace_path, target_file)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target file for bug injection not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Clean up newlines to be platform independent (Windows vs Unix)
        content_norm = content.replace("\r\n", "\n")
        orig_norm = original_content.replace("\r\n", "\n")
        buggy_norm = buggy_content.replace("\r\n", "\n")
        
        if orig_norm not in content_norm:
            raise ValueError(f"Original content to replace not found in target file: {file_path}")
            
        new_content = content_norm.replace(orig_norm, buggy_norm, 1)
        
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
            
        print(f"💉 [INJECTOR] Injected bug successfully into {target_file}")
        return file_path


class PreValidator:
    """Validates the state of the workspace after bug injection to ensure clean failure."""
    
    @staticmethod
    def validate(workspace_path: str, bug_type: str, build_cmd: List[str], val_cmd: List[str]) -> bool:
        print(f"🔍 [PRE-VALIDATE] Checking injected bug behavior (type: {bug_type})...")
        
        compilation_bugs = {"MissingImport", "CompilationError", "MissingMethod", "MissingClass"}
        
        # Run build command
        print(f"   Running build: {' '.join(build_cmd)}")
        build_res = subprocess.run(
            build_cmd,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            shell=True
        )
        
        if bug_type in compilation_bugs:
            # For compile-time bugs, build MUST fail
            if build_res.returncode != 0:
                print("   ✅ [PRE-VALIDATE] Build failed as expected for compile-time bug.")
                return True
            else:
                print("   ❌ [PRE-VALIDATE] Build unexpectedly succeeded for compile-time bug!")
                return False
        else:
            # For runtime bugs, build MUST pass
            if build_res.returncode == 0:
                # Run validation command, which MUST fail
                print(f"   Running validation tests: {' '.join(val_cmd)}")
                val_res = subprocess.run(
                    val_cmd,
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if val_res.returncode != 0:
                    print("   ✅ [PRE-VALIDATE] Build succeeded and validation tests failed as expected.")
                    return True
                else:
                    print("   ❌ [PRE-VALIDATE] Validation tests unexpectedly passed for runtime bug!")
                    return False
            else:
                print(f"   ❌ [PRE-VALIDATE] Build failed unexpectedly for runtime bug! Error:\n{build_res.stderr}")
                return False


async def run_baseline_a(workspace_path: str, testcase_data: dict, llm_client: OpenAIClient) -> dict:
    """Baseline A: Pure LLM (Single Prompt direct code generator)"""
    print("🚀 [BASELINE A] Starting Pure LLM Execution...")
    start_time = time.time()
    entry_file = testcase_data["entry_file"]
    file_path = os.path.join(workspace_path, entry_file)
    
    with open(file_path, "r", encoding="utf-8") as f:
        original_code = f.read()
        
    system_prompt = (
        "You are an AI software engineering assistant. You are given a file containing a bug, "
        "the compiler stacktrace/error message, and the task description. Your job is to fix the bug "
        "and return the complete updated content of the file. Return ONLY the complete, drop-in replacement "
        "file content inside a JSON object with a single key 'patched_code'. Output ONLY valid JSON."
    )
    user_prompt = (
        f"File Path: {entry_file}\n\n"
        f"Task: {testcase_data['task']}\n\n"
        f"Stacktrace:\n{testcase_data['stacktrace']}\n\n"
        f"Original File Content:\n{original_code}"
    )
    
    # Reset token counts in client
    llm_client.total_prompt_tokens = 0
    llm_client.total_completion_tokens = 0
    
    termination_reason = "SUCCESS"
    failure_category = "NONE"
    
    try:
        response_text = await llm_client.call(system_prompt, user_prompt)
        try:
            response_json = json.loads(response_text)
            patched_code = response_json.get("patched_code", "")
        except Exception:
            patched_code = response_text
            
        if not patched_code:
            patched_code = response_text
            
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(patched_code)
            
    except Exception as e:
        print(f"❌ [BASELINE A] Error during execution: {e}")
        termination_reason = "AGENT_CRASH"
        failure_category = "PARSING_ERROR"
        
    latency_ms = int((time.time() - start_time) * 1000)
    prompt_tokens = llm_client.total_prompt_tokens
    completion_tokens = llm_client.total_completion_tokens
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1000000.0
    
    return {
        "passed": False,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "termination_reason": termination_reason,
        "failure_category": failure_category,
        "step_count": 1,
        "loop_prevented": False,
        "selected_skills": ["pure-llm-call"],
        "node_trace": [{
            "node_id": "pure_llm_call",
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "selected_skill": "pure-llm-call",
            "summary": "Invoked model directly to generate patch"
        }]
    }


async def run_baseline_b(workspace_path: str, testcase_data: dict, llm_client: OpenAIClient, skill_client: SkillExecutionClient) -> dict:
    """Baseline B: Top-1 Similarity (Direct skill matcher without planning)"""
    print("🚀 [BASELINE B] Starting Top-1 Similarity Execution...")
    start_time = time.time()
    
    # 1. Select the top-1 skill using semantic registry
    stacktrace = testcase_data["stacktrace"]
    hits = semantic_registry.search(stacktrace, top_k=1)
    if not hits:
        best_skill_name = "suggest-java-fix" if testcase_data["language"] == "java" else "suggest-python-fix"
    else:
        best_skill_name = hits[0][0]
        
    print(f"🎯 [BASELINE B] Top-1 selected skill: {best_skill_name}")
        
    # Reset token counts in client
    llm_client.total_prompt_tokens = 0
    llm_client.total_completion_tokens = 0
    
    # 2. Invoke parameter extraction and run the skill
    from services.skill_testing.core.execute_node import execute_node
    from services.skill_testing.state import AgentState
    
    entry_file = testcase_data["entry_file"]
    file_path = os.path.join(workspace_path, entry_file)
    with open(file_path, "r", encoding="utf-8") as f:
        original_code = f.read()
        
    state = AgentState(
        user_context={
            "code": original_code,
            "filename": entry_file,
            "stacktrace": stacktrace,
            "message": testcase_data["task"]
        },
        plan=[best_skill_name],
        current_step_idx=0,
        selected_skill=best_skill_name,
        history=[]
    )
    
    termination_reason = "SUCCESS"
    failure_category = "NONE"
    
    try:
        state = await execute_node(state, llm_client, skill_client)
        if state.last_observation and "FAILED" in state.last_observation:
            termination_reason = "AGENT_CRASH"
            failure_category = "EXECUTION_ERROR"
    except Exception as e:
        print(f"❌ [BASELINE B] Error executing skill {best_skill_name}: {e}")
        termination_reason = "AGENT_CRASH"
        failure_category = "EXECUTION_ERROR"
        
    latency_ms = int((time.time() - start_time) * 1000)
    prompt_tokens = llm_client.total_prompt_tokens
    completion_tokens = llm_client.total_completion_tokens
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1000000.0
    
    return {
        "passed": False,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "termination_reason": termination_reason,
        "failure_category": failure_category,
        "step_count": state.step_count,
        "loop_prevented": False,
        "selected_skills": [best_skill_name],
        "node_trace": [{
            "node_id": "execute_node",
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "selected_skill": best_skill_name,
            "summary": f"Executed selected Top-1 skill: {best_skill_name}"
        }]
    }


async def run_cass_orchestrator(workspace_path: str, testcase_data: dict, llm_client: OpenAIClient, skill_client: SkillExecutionClient) -> dict:
    """Proposed Method: CASS Orchestrator (Full Graph loop with feedback and loops detection)"""
    print("🚀 [CASS ORCHESTRATOR] Starting Full Graph Execution...")
    start_time = time.time()
    
    from services.skill_testing.orchestrator import get_compiled_workflow
    from services.skill_testing.state import AgentState
    
    entry_file = testcase_data["entry_file"]
    file_path = os.path.join(workspace_path, entry_file)
    with open(file_path, "r", encoding="utf-8") as f:
        original_code = f.read()
        
    # Reset token counts in client
    llm_client.total_prompt_tokens = 0
    llm_client.total_completion_tokens = 0
    
    initial_state = {
        "user_context": {
            "code": original_code,
            "filename": entry_file,
            "stacktrace": testcase_data["stacktrace"],
            "message": testcase_data["task"]
        },
        "plan": [],
        "current_step_idx": 0,
        "step_count": 0,
        "history": []
    }
    
    app = get_compiled_workflow(llm_client, skill_client)
    
    termination_reason = "SUCCESS"
    failure_category = "NONE"
    loop_prevented = False
    final_state = {}
    
    try:
        final_state = await app.ainvoke(initial_state)
        
        # Analyze state properties
        step_count = final_state.get("step_count", 0) if isinstance(final_state, dict) else getattr(final_state, "step_count", 0)
        max_total_steps = final_state.get("max_total_steps", 12) if isinstance(final_state, dict) else getattr(final_state, "max_total_steps", 12)
        is_finished = final_state.get("is_finished", False) if isinstance(final_state, dict) else getattr(final_state, "is_finished", False)
        final_answer = final_state.get("final_answer", "") if isinstance(final_state, dict) else getattr(final_state, "final_answer", "")
        
        if "LOOP" in str(final_answer) or "CIRCUIT" in str(final_answer):
            loop_prevented = True
            termination_reason = "LOOP_DETECTED"
            failure_category = "TIMEOUT"
        elif not is_finished:
            if step_count >= max_total_steps:
                termination_reason = "MAX_STEPS_EXCEEDED"
                failure_category = "TIMEOUT"
            else:
                termination_reason = "AGENT_CRASH"
                failure_category = "EXECUTION_ERROR"
                
    except Exception as e:
        print(f"❌ [CASS ORCHESTRATOR] Error during execution: {e}")
        termination_reason = "AGENT_CRASH"
        failure_category = "EXECUTION_ERROR"
        
    latency_ms = int((time.time() - start_time) * 1000)
    prompt_tokens = llm_client.total_prompt_tokens
    completion_tokens = llm_client.total_completion_tokens
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1000000.0
    
    # Extract selected skills
    selected_skills = []
    history = final_state.get("history", []) if isinstance(final_state, dict) else getattr(final_state, "history", [])
    for entry in history:
        if "skill" in entry:
            selected_skills.append(entry["skill"])
            
    # Extract node trace
    node_trace = []
    execution_history = final_state.get("execution_history", []) if isinstance(final_state, dict) else getattr(final_state, "execution_history", [])
    for idx, entry in enumerate(execution_history):
        node_trace.append({
            "node_id": entry.get("node", f"step_{idx}"),
            "latency_ms": entry.get("latency_ms", 0),
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            "cost_usd": (entry.get("prompt_tokens", 0) * 0.15 + entry.get("completion_tokens", 0) * 0.60) / 1000000.0,
            "selected_skill": entry.get("node", ""),
            "summary": f"Executed node: {entry.get('node')}"
        })
        
    return {
        "passed": False,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "termination_reason": termination_reason,
        "failure_category": failure_category,
        "step_count": final_state.get("step_count", 1) if isinstance(final_state, dict) else getattr(final_state, "step_count", 1),
        "loop_prevented": loop_prevented,
        "selected_skills": selected_skills,
        "node_trace": node_trace
    }


def verify_solution(workspace_path: str, expected_config: dict) -> tuple[bool, str]:
    """Runs compilation, unit test suites, and patch assertions to verify a fix."""
    print("🧪 [VALIDATION] Running validation checks...")
    targets = expected_config["validation_targets"]
    
    # 1. Compilation check
    if targets.get("verify_compilation"):
        comp_assertion = expected_config["compilation_assertion"]
        print(f"   Compiling: {' '.join(comp_assertion['command'])}")
        res = subprocess.run(
            comp_assertion["command"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            shell=True
        )
        if res.returncode != comp_assertion["expected_exit_code"]:
            print(f"   ❌ Compilation failed with exit code: {res.returncode}")
            return False, "COMPILATION_ERROR"
            
    # 2. Test suite check
    if targets.get("verify_tests"):
        test_assertion = expected_config["test_assertion"]
        print(f"   Running tests: {' '.join(test_assertion['command'])}")
        res = subprocess.run(
            test_assertion["command"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            shell=True
        )
        if res.returncode != test_assertion["expected_exit_code"]:
            print(f"   ❌ Test suite failed with exit code: {res.returncode}")
            return False, "TEST_FAILURE"
            
    # 3. Patch check
    if targets.get("verify_patch"):
        patch_assertion = expected_config["patch_assertion"]
        for rel_file in patch_assertion["modified_files"]:
            file_path = os.path.join(workspace_path, rel_file)
            if not os.path.exists(file_path):
                print(f"   ❌ Required modified file not found: {rel_file}")
                return False, "PATCH_VERIFICATION_FAILURE"
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Check required patterns
            for pattern in patch_assertion.get("required_patterns", []):
                if pattern not in content:
                    print(f"   ❌ Required pattern not found in file: {pattern}")
                    return False, "PATCH_VERIFICATION_FAILURE"
            # Check prohibited patterns
            for pattern in patch_assertion.get("prohibited_patterns", []):
                if pattern in content:
                    print(f"   ❌ Prohibited pattern found in file: {pattern}")
                    return False, "PATCH_VERIFICATION_FAILURE"
                    
    print("   ✅ [VALIDATION] All assertions passed successfully!")
    return True, "NONE"
