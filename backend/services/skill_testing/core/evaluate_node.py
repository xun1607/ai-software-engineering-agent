import json
import re
import os
from services.skill_testing.state import AgentState

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
    
    response = await model_client.call(system_prompt, "Evaluate the result.")
    
    # Sync token usage
    state.prompt_tokens = getattr(model_client, "total_prompt_tokens", 0)
    state.completion_tokens = getattr(model_client, "total_completion_tokens", 0)
    state.total_tokens = state.prompt_tokens + state.completion_tokens

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
            if skill_client:
                # TỰ ĐỘNG PHÂN ĐỊNH ĐƯỜNG DẪN THEO NGÔN NGỮ trong client
                skill_client.setup_initial_workspace(content, target_name)
            else:
                fallback_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace")
                )
                if target_name.endswith(".java"):
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
            if target_name.endswith(".java"):
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
