import json
import re
import os
import time
from services.skill_testing.state import AgentState

def extract_normalized_error(observation_str: str) -> str:
    if not observation_str:
        return "GENERIC_ERROR"
    
    try:
        data = json.loads(observation_str)
        if isinstance(data, dict):
            err_text = " ".join([
                str(data.get("stderr", "")),
                str(data.get("stdout", "")),
                str(data.get("message", ""))
            ]).strip()
        else:
            err_text = str(data)
    except Exception:
        err_text = observation_str

    if not err_text:
        return "GENERIC_ERROR"

    # Regex so khớp các Exception/Error phổ biến
    if re.search(r"NullPointerException", err_text, re.IGNORECASE):
        return "NullPointerException"
    
    if re.search(r"ModuleNotFoundError|ImportError", err_text, re.IGNORECASE):
        module_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", err_text)
        if module_match:
            return f"ModuleNotFoundError: {module_match.group(1)}"
        return "ModuleNotFoundError"
        
    if re.search(r"cannot find symbol", err_text, re.IGNORECASE):
        symbol_match = re.search(r"symbol:\s+(?:class|method|variable|package)\s+([^\n]+)", err_text)
        if symbol_match:
            return f"cannot find symbol: {symbol_match.group(1).strip()}"
        return "cannot find symbol"
        
    if re.search(r"ArithmeticException", err_text, re.IGNORECASE):
        return "ArithmeticException"
        
    if re.search(r"FileNotFoundError", err_text, re.IGNORECASE):
        return "FileNotFoundError"

    if "FAILED" in err_text or "error" in err_text.lower() or "exception" in err_text.lower() or "fail" in err_text.lower():
        return "GENERIC_ERROR"

    return "SUCCESS_OR_NO_ERROR"

async def evaluate_node(state: AgentState, model_client, skill_client=None):
    state.step_count += 1
    if state.step_count > state.max_total_steps:
        state.is_finished = True
        state.final_answer = f"TERMINATED: Safety limit reached ({state.max_total_steps} steps). Potential infinite loop."
        return state

    if not state.plan or state.current_step_idx >= len(state.plan):
        state.is_finished = True
        state.final_answer = "TERMINATED: No active plan to evaluate."
        return state

    current_task = state.plan[state.current_step_idx]
    
    # 1. Loop Detection chuẩn hóa (TASK_XA)
    normalized_err = extract_normalized_error(state.last_observation)
    task_name = current_task or "None"
    skill_name = state.selected_skill or "None"
    fingerprint = (task_name, skill_name, normalized_err)
    
    state.fingerprint_history.append(fingerprint)
    
    if len(state.fingerprint_history) >= 3:
        if state.fingerprint_history[-1] == state.fingerprint_history[-2] == state.fingerprint_history[-3]:
            print(f"🚨 [LOOP DETECTED] Phát hiện vòng lặp thực thi 3 lần liên tiếp: {fingerprint}")
            state.need_replan = True
            state.is_finished = True
            state.final_answer = f"TERMINATED: Infinite loop detected. Repeating execution fingerprint 3 times: {fingerprint}"
            return state

    # Sử dụng LLM Evaluator để phân tích cú pháp lỗi và phát hiện thiếu hụt tài nguyên
    system_prompt = f"""
    You are a Quality Assurance Engineer evaluating the task execution.
    GOAL: {state.goal or state.user_context.get('message', 'Fix the bug')}
    CURRENT TASK: {current_task}
    OBSERVATION: {state.last_observation}
    
    INSTRUCTIONS:
    1. Evaluate if the current task succeeded. If the observation shows the task succeeded or the goal for this step is met, set "is_success" to true.
    2. If the task failed due to a missing file, class, dependency, resource, or library (for example, a compilation error like "cannot find symbol", "package does not exist", "ModuleNotFoundError", "ImportError", or a missing import/class definition), you must set "need_dynamic_intervention" to true.
    3. If "need_dynamic_intervention" is true, provide an intervention plan in the "intervention" field with:
        - "action": "create_file"
        - "target_name": the name of the missing resource/file to generate (e.g. "User.java", "Config.py", etc.)
        - "content": the code/content to create the file or stub class
        - "task_to_inject": the task description to inject back into the plan to verify the fix (e.g., rerun the current compilation task like "debug-java-null-pointer")
    4. If no intervention is needed, set "need_dynamic_intervention" to false.
    5. Output ONLY a valid JSON object matching this schema, no markdown blocks, no extra text.
    """
    
    start_time = time.time()
    response = await model_client.call(system_prompt, "Evaluate the result.")
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Sync và log tokens/latency (TASK_1B / Phase 2)
    usage = getattr(model_client, "last_call_usage", None) or {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "model": "gpt-4o-mini",
        "cost": 0.0
    }
    
    history_entry = {
        "node": "evaluate_node",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "latency_ms": latency_ms,
        "model": usage.get("model", "gpt-4o-mini")
    }
    state.execution_history.append(history_entry)
    
    # Sync token usage và cộng cost vào state
    state.prompt_tokens = getattr(model_client, "total_prompt_tokens", 0)
    state.completion_tokens = getattr(model_client, "total_completion_tokens", 0)
    state.total_tokens = state.prompt_tokens + state.completion_tokens
    state.total_cost += usage.get("cost", 0.0)

    try:
        # Loại bỏ định dạng markdown nếu có
        cleaned_response = response.strip()
        if "```" in cleaned_response:
            code_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_response, re.DOTALL | re.IGNORECASE)
            if code_match:
                cleaned_response = code_match.group(1).strip()
                
        evaluation = json.loads(cleaned_response)
        is_success = evaluation.get("is_success", False)
        analysis = evaluation.get("analysis", "No analysis provided.")
        need_dynamic_intervention = evaluation.get("need_dynamic_intervention", False)
        intervention = evaluation.get("intervention", {})
    except Exception as e:
        is_success = False 
        analysis = f"Failed to parse evaluation JSON: {str(e)}"
        need_dynamic_intervention = False
        intervention = {}

    # Thực hiện Can thiệp động (Dynamic Intervention)
    if need_dynamic_intervention and intervention:
        action = intervention.get("action")
        target_name = intervention.get("target_name")
        content = intervention.get("content", "")
        task_to_inject = intervention.get("task_to_inject")

        print(f"⚠️ [DYNAMIC INTERVENTION] Triggered action '{action}' for '{target_name}'")
        
        if action == "create_file" and target_name:
            entry_file = state.user_context.get("filename", "")
            if skill_client:
                if entry_file and ("/" in entry_file or "\\" in entry_file):
                    dest_dir = os.path.join(skill_client.workspace_dir, os.path.dirname(entry_file))
                    os.makedirs(dest_dir, exist_ok=True)
                    file_path = os.path.join(dest_dir, target_name)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                else:
                    skill_client.setup_initial_workspace(content, target_name)
            else:
                fallback_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace")
                )
                if entry_file and ("/" in entry_file or "\\" in entry_file):
                    fallback_dir = os.path.join(fallback_dir, os.path.dirname(entry_file))
                elif target_name.endswith(".java"):
                    fallback_dir = os.path.join(fallback_dir, "src", "main", "java")
                os.makedirs(fallback_dir, exist_ok=True)
                file_path = os.path.join(fallback_dir, target_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            print(f"💾 [DYNAMIC INTERVENTION] Created file vật lý: {target_name}")
        else:
            # Ghi đè trực tiếp fallback an toàn
            fallback_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace")
            )
            entry_file = state.user_context.get("filename", "")
            if entry_file and ("/" in entry_file or "\\" in entry_file):
                fallback_dir = os.path.join(fallback_dir, os.path.dirname(entry_file))
            elif target_name.endswith(".java"):
                fallback_dir = os.path.join(fallback_dir, "src", "main", "java")
                
            os.makedirs(fallback_dir, exist_ok=True)
            with open(os.path.join(fallback_dir, target_name), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"💾 [DYNAMIC INTERVENTION] Wrote file directly to fallback path: {target_name}")

        if task_to_inject:
            current_task = state.plan[state.current_step_idx] if state.current_step_idx < len(state.plan) else None
            next_task = state.plan[state.current_step_idx + 1] if state.current_step_idx + 1 < len(state.plan) else None
            
            if task_to_inject == current_task or task_to_inject == next_task:
                print(f"⏭️ [TASK INJECTION PREVENTED] Task '{task_to_inject}' is already at current/next position. No duplication needed.")
            else:
                state.plan.insert(state.current_step_idx, task_to_inject)
                print(f"💉 [TASK INJECTION] Injected task '{task_to_inject}' at index {state.current_step_idx}")

        state.retry_count = 0  # Đặt về 0 để bộ định tuyến route_decision đưa đồ thị đi qua select_skill_node chọn kỹ năng mới
        state.reflection.append(f"🔄 Dynamic intervention: Created {target_name}. Injected task {task_to_inject}.")
        state.last_observation = json.dumps({
            "status": "SUCCESS", 
            "message": f"Intervention completed: {target_name} created.", 
            "stdout": f"Created {target_name} successfully."
        })
        return state

    if is_success:
        state.retry_count = 0 
        state.reflection.append(f"✅ Step {state.current_step_idx + 1} Success: {analysis}")
        state.current_step_idx += 1
        
        if state.current_step_idx >= len(state.plan):
            state.is_finished = True
            state.final_answer = f"SUCCESS: All steps completed. Final analysis: {analysis}"
        else:
            state.selected_skill = None
            state.last_observation = None
    
    else:
        state.reflection.append(f"❌ Step {state.current_step_idx + 1} Failed: {analysis}")
        
        if state.retry_count < 1: # Cho phép thử lại 1 lần (tổng 2 lần chạy)
            state.retry_count += 1

        elif state.replan_count < state.max_replans:
            state.replan_count += 1
            state.retry_count = 0
            state.plan = []
            state.current_step_idx = 0
            state.reflection.append(f"🔄 Re-planning attempt {state.replan_count}/{state.max_replans} due to failure.")
        
        else:
            state.is_finished = True
            state.final_answer = generate_fallback_suggestion(state)

    return state

def generate_fallback_suggestion(state: AgentState) -> str:
    """Tạo báo cáo lỗi và gợi ý (Helper function - không dùng 'self')"""
    summary = "❌ FAILED: I have exhausted all retries and re-planning attempts.\n"
    summary += f"- Steps attempted: {state.step_count}\n"
    summary += f"- Last failure: {state.reflection[-1] if state.reflection else 'Unknown'}\n"
    if hasattr(state, 'missing_skills_log') and state.missing_skills_log:
        summary += f"- Missing tools for: {', '.join(state.missing_skills_log)}\n"
    summary += "\nSUGGESTION: The task might require a skill not currently in the library, or the provided source code/context is insufficient."
    return summary
