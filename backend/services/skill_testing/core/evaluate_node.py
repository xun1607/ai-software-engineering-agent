import json
import re
import os
import time
from services.skill_testing.state import AgentState
from shared.db import get_session
from services.skill_testing.models import AgentExecutionLog

def extract_normalized_error(observation_str: str) -> str:
    """Classifies raw errors from execution logs into standardized categories."""
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

def detect_loop(state: AgentState, current_task: str, normalized_err: str) -> bool:
    """Checks the history to detect if the agent is stuck in an infinite loop."""
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
            return True
    return False

async def call_llm_evaluator(model_client, state: AgentState, current_task: str) -> tuple[dict, int]:
    """Invokes LLM to check step quality and detect missing dependencies."""
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
    
    # Clean markdown formatting
    cleaned_response = response.strip()
    if "```" in cleaned_response:
        code_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_response, re.DOTALL | re.IGNORECASE)
        if code_match:
            cleaned_response = code_match.group(1).strip()
            
    try:
        evaluation = json.loads(cleaned_response)
    except Exception as e:
        print(f"⚠️ [EVALUATOR] Failed to parse evaluation JSON: {e}")
        evaluation = {
            "is_success": False,
            "analysis": f"Failed to parse evaluation JSON: {str(e)}",
            "need_dynamic_intervention": False,
            "intervention": {}
        }
    return evaluation, latency_ms

def apply_dynamic_intervention(skill_client, entry_file: str, intervention: dict):
    """Creates stub classes physically on disk when compilation/runtime dependencies are missing."""
    action = intervention.get("action")
    target_name = intervention.get("target_name")
    content = intervention.get("content", "")
    
    print(f"⚠️ [DYNAMIC INTERVENTION] Triggered action '{action}' for '{target_name}'")
    
    if action == "create_file" and target_name:
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
        fallback_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace")
        )
        if entry_file and ("/" in entry_file or "\\" in entry_file):
            fallback_dir = os.path.join(fallback_dir, os.path.dirname(entry_file))
        elif target_name.endswith(".java"):
            fallback_dir = os.path.join(fallback_dir, "src", "main", "java")
            
        os.makedirs(fallback_dir, exist_ok=True)
        with open(os.path.join(fallback_dir, target_name), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"💾 [DYNAMIC INTERVENTION] Wrote file directly to fallback path: {target_name}")

def route_next_state(state: AgentState, is_success: bool, analysis: str) -> AgentState:
    """Updates state machine properties (retry counts, finish status, plan indices)."""
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
        
        if state.retry_count < 1:  # Allow 1 retry
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

async def evaluate_node(state: AgentState, model_client, skill_client=None) -> AgentState:
    """
    Node đánh giá (Evaluator): Node kiểm tra kết quả thực thi của task hiện tại và 
    quyết định trạng thái thực thi tiếp theo của Agent. Ngoài việc kiểm tra task đang thực hiện có thành công hay không, 
    node còn thực hiện các kiểm tra an toàn, gọi LLM để đánh giá chất lượng kết quả, hỗ trợ cơ chế tự phục hồi 
    (Dynamic Self-Healing) và cập nhật các chỉ số thực thi
    
    Chức năng:
    1. Dừng quá trình thực thi khi vượt quá các ngưỡng an toàn hoặc không còn kế hoạch hợp lệ.
    2. Phát hiện các lần thất bại lặp lại để tránh vòng lặp thực thi vô hạn.
    3. Gọi bộ đánh giá dựa trên LLM để xác định task hiện tại đã hoàn thành thành công hay chưa.
    4. Ghi nhận các chỉ số thực thi như số lượng token, độ trễ (latency) và các metrics liên quan.
    5. Thực hiện can thiệp động (Dynamic Intervention / Self-Healing) khi bộ đánh giá đề xuất hành động khôi phục.
    6. Quyết định trạng thái tiếp theo của Agent (tiếp tục, thử lại, lập kế hoạch lại hoặc kết thúc).
    """
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
    
    # Loop Detection
    normalized_err = extract_normalized_error(state.last_observation)
    if detect_loop(state, current_task, normalized_err):
        return state

    # 3. Đánh giá kết quả khách quan dựa trên Environment Validator hoặc Executor Status
    validation_feedback = state.user_context.get("validation_feedback")
    
    is_success = False
    analysis = "No analysis provided."
    need_dynamic_intervention = False
    intervention = {}
    latency_ms = 0
    
    # Kiểm tra nếu bước này có chạy Environment Validator
    if validation_feedback is not None:
        is_success = (validation_feedback["exit_code"] == 0)
        analysis = "Environment Validator: Passed." if is_success else f"Environment Validator Failed. Error:\n{validation_feedback['stderr']}"
        print(f"🛡️ [EVALUATOR] Sử dụng kết quả khách quan từ Environment Validator. Success: {is_success}")
        
        # Nếu thất bại, gọi LLM để phân tích khả năng tự phục hồi (Self-Healing) chèn stub file
        if not is_success:
            print("🛡️ [EVALUATOR] Validator thất bại. Gọi LLM để phân tích khả năng tự phục hồi (Self-Healing)...")
            evaluation, latency_ms = await call_llm_evaluator(model_client, state, current_task)
            need_dynamic_intervention = evaluation.get("need_dynamic_intervention", False)
            intervention = evaluation.get("intervention", {})
            analysis += f"\nLLM Analysis: {evaluation.get('analysis', '')}"
    else:
        # Nếu không có validator (các skill đọc file, parse stacktrace), kiểm tra trạng thái Executor
        try:
            obs_data = json.loads(state.last_observation) if state.last_observation else {}
            obs_status = obs_data.get("status", "SUCCESS")
        except Exception:
            obs_status = "SUCCESS"
            
        is_success = (obs_status.upper() == "SUCCESS")
        analysis = "Executor completed successfully." if is_success else "Executor execution failed."
        print(f"🛡️ [EVALUATOR] Sử dụng trạng thái thực thi của Executor. Success: {is_success}")
        
        # Nếu Executor chính thất bại, gọi LLM phân tích khả năng tự phục hồi
        if not is_success:
            print("🛡️ [EVALUATOR] Executor thất bại. Gọi LLM để phân tích khả năng tự phục hồi...")
            evaluation, latency_ms = await call_llm_evaluator(model_client, state, current_task)
            need_dynamic_intervention = evaluation.get("need_dynamic_intervention", False)
            intervention = evaluation.get("intervention", {})
            analysis += f"\nLLM Analysis: {evaluation.get('analysis', '')}"
            
    # Ghi vào execution logs
    usage = getattr(model_client, "last_call_usage", None) if (not is_success or validation_feedback is None) else {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "model": "environment_validator",
        "cost": 0.0
    }
    if not usage:
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": "local_evaluator",
            "cost": 0.0
        }
        
    history_entry = {
        "node": "evaluate_node",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "latency_ms": latency_ms,
        "model": usage.get("model", "gpt-4o-mini" if (not is_success) else "local_validator")
    }
    state.execution_history.append(history_entry)
    
    # Sync token usage counts
    state.prompt_tokens = getattr(model_client, "total_prompt_tokens", 0)
    state.completion_tokens = getattr(model_client, "total_completion_tokens", 0)
    state.total_tokens = state.prompt_tokens + state.completion_tokens
    state.total_cost += usage.get("cost", 0.0)
    
    last_log_id = state.user_context.get("last_log_id")
    if last_log_id:
        try:
            with get_session() as session:
                log_entry = session.query(AgentExecutionLog).filter_by(id=last_log_id).first()
                if log_entry:
                    log_entry.success = is_success
                    log_entry.quality = 1.0 if is_success else 0.0
                    session.commit()
                    print(f"🔄 [DB UPDATE] Đã đồng bộ kết quả thực tế vào SQLite cho Log ID: {last_log_id} | Success: {is_success}")
        except Exception as db_update_err:
            print(f"⚠️ [DB UPDATE ERROR] Không thể cập nhật kết quả vào SQLite: {db_update_err}")

    # Handle Self-healing (Dynamic Intervention)
    if need_dynamic_intervention and intervention:
        apply_dynamic_intervention(skill_client, state.user_context.get("filename", ""), intervention)
        
        task_to_inject = intervention.get("task_to_inject")
        if task_to_inject:
            next_task = state.plan[state.current_step_idx + 1] if state.current_step_idx + 1 < len(state.plan) else None
            if task_to_inject == current_task or task_to_inject == next_task:
                print(f"⏭️ [TASK INJECTION PREVENTED] Task '{task_to_inject}' is already at current/next position. No duplication needed.")
            else:
                state.plan.insert(state.current_step_idx, task_to_inject)
                print(f"💉 [TASK INJECTION] Injected task '{task_to_inject}' at index {state.current_step_idx}")

        state.retry_count = 0  # reset retries for injected recovery task
        state.reflection.append(f"🔄 Dynamic intervention: Created {intervention.get('target_name')}. Injected task {task_to_inject}.")
        state.last_observation = json.dumps({
            "status": "SUCCESS", 
            "message": f"Intervention completed: {intervention.get('target_name')} created.", 
            "stdout": f"Created {intervention.get('target_name')} successfully."
        })
        return state

    # State transitions (Success / Fail / Retry / Replan)
    state = route_next_state(state, is_success, analysis)
    return state

def generate_fallback_suggestion(state: AgentState) -> str:
    """Generates failure description report."""
    summary = "❌ FAILED: Đã thử lại tối đa số lần (1) và replan nhưng không thành công.\n"
    summary += f"- Steps attempted: {state.step_count}\n"
    summary += f"- Last failure: {state.reflection[-1] if state.reflection else 'Unknown'}\n"
    if hasattr(state, 'missing_skills_log') and state.missing_skills_log:
        summary += f"- Missing tools for: {', '.join(state.missing_skills_log)}\n"
    summary += "\nSUGGESTION: The task might require a skill not currently in the library, or the provided source code/context is insufficient."
    return summary
