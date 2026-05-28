import json
from backend.services.skill_testing.core.registry import semantic_registry
from backend.services.skill_testing.state import AgentState

def select_skill_node(state: AgentState, model_client, registry):
    current_task = state.plan[state.current_step_idx]
    state.current_task = current_task
    # Step 1: Semantic Search de tim ung vien skill
    candidates = registry.search(current_task, top_k=4)
    if not candidates:
        state.selected_skill = None
        state.last_thought = "No candidates found in semantic registry."
        return state

    # Chuan bi thong tin cho LLM chon (Step 2: Re-ranking)
    candidates_info = ""
    for i, (skill, score) in enumerate(candidates):
        candidates_info += f"{i+1}. NAME: {skill.name}\n   DESCRIPTION: {skill.metadata.get('description', '')}\n\n"

    system_prompt = f"""
    You are a Task Dispatcher. Your job is to select the BEST skill to perform a specific task.
    CANDIDATE SKILLS:
    {candidates_info}
    INSTRUCTIONS:
    1. Compare the task with the descriptions of the candidate skills.
    2. Choose the skill that perfectly matches the task's requirements.
    3. If none of the skills are suitable, return 'NONE'.
    4. Provide your thought process and the final selected skill name in JSON.
    """
    user_prompt = f"TASK TO PERFORM: {current_task}"

    response = model_client.call(system_prompt, user_prompt)
    
    try:
        # Ky vong JSON: {"thought": "...", "selected_skill": "..."}
        decision = json.loads(response)
        state.last_thought = decision.get("thought", "")
        
        selected_name = decision.get("selected_skill")
        if selected_name == "NONE":
            state.selected_skill = None
        else:
            state.selected_skill = selected_name
            
    except Exception as e:
        # Fallback: Lay luon skill dung dau semantic search neu LLM crash
        state.selected_skill = candidates[0][0].name
        state.last_thought = f"LLM Selection failed, falling back to top semantic match. Error: {e}"
        
    return state