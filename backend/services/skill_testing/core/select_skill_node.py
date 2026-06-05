import json
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.state import AgentState

def select_skill_node(state: AgentState):
    print("--- [Skill Selection Node] Choosing the best skill for the current task ---")
    current_task = state.plan[state.current_step_idx]
    state.current_task = current_task
    print(f"Nhiệm vụ hiện tại: {current_task}")
    # Semantic Search de tim ung vien skill

    matched_skill = semantic_registry.get_skill_by_name(current_task)
    if matched_skill:
        state.selected_skill = matched_skill
        state.last_thought = f"Semantic registry found an exact match for the task: {matched_skill}"
        print(f"Khớp thành công kỹ năng: {state.selected_skill}")
    else:
        state.selected_skill = None
        state.last_thought =f"CRITICAL: Capability '{current_task}' does not exist in system registry"
    
    return state

    # # Chuan bi thong tin cho LLM chon (Step 2: Re-ranking)
    # candidates_info = ""
    # for i, (skill, score) in enumerate(candidates):
    #     candidates_info += f"{i+1}. NAME: {skill.name}\n   DESCRIPTION: {skill.metadata.get('description', '')}\n\n"

    # system_prompt = f"""
    # You are a Task Dispatcher. Your job is to select the BEST skill to perform a specific task.
    # CANDIDATE SKILLS:
    # {candidates_info}
    # INSTRUCTIONS:
    # 1. Compare the task with the descriptions of the candidate skills.
    # 2. Choose the skill that perfectly matches the task's requirements.
    # 3. If none of the skills are suitable, return 'NONE'.
    # 4. Provide your thought process and the final selected skill name in JSON.
    # """
    # user_prompt = f"TASK TO PERFORM: {current_task}"

    # response = model_client.call(system_prompt, user_prompt)
    
    # try:
    #     # Ky vong JSON: {"thought": "...", "selected_skill": "..."}
    #     decision = json.loads(response)
    #     state.last_thought = decision.get("thought", "")
        
    #     selected_name = decision.get("selected_skill")
    #     if selected_name == "NONE":
    #         state.selected_skill = None
    #     else:
    #         state.selected_skill = selected_name
            
    # except Exception as e:
    #     # Fallback: Lay luon skill dung dau semantic search neu LLM crash
    #     state.selected_skill = candidates[0][0].name
    #     state.last_thought = f"LLM Selection failed, falling back to top semantic match. Error: {e}"
        
    # return state