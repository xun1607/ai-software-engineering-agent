import json
from services.skill_testing.state import AgentState

def evaluate_node(state: AgentState, model_client):
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
    
    system_prompt = f"""
    You are a Quality Assurance Engineer. Evaluate if the task was completed successfully based on the observation.
    GOAL: {state.goal or state.user_context['message']}
    CURRENT TASK: {current_task}
    OBSERVATION: {state.last_observation}
    INSTRUCTIONS:
    - If the observation shows the task succeeded or the goal for this step is met, return {{"is_success": true, "analysis": "..."}}
    - If it failed, timed out, or returned an error, return {{"is_success": false, "analysis": "..."}}
    - Output ONLY JSON.
    """
    response = model_client.call(system_prompt, "Evaluate the result.")
    try:
        evaluation = json.loads(response)
        is_success = evaluation.get("is_success", False)
        analysis = evaluation.get("analysis", "No analysis provided.")
    except Exception as e:
        is_success = False 
        analysis = f"Failed to parse evaluation JSON: {str(e)}"

    
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