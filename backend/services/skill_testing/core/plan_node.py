# import json

# from backend.services.skill_testing.core.skill_manager import SkillManager
# from backend.services.skill_testing.state import AgentState

# def plan_node(state: AgentState, model_client, registry):
#     """ Node lap ke hoach: Phan ra task dua tren capability cac skill va context"""
#     capabilities = SkillManager.get_capabilities(registry)
    
#     system_prompt = f"""
#     You are an expert Software Engineer AI, Your goal is to solve the user's software engineering problem by breaking it down into smaller tasks and assigning them to the appropriate skills.
#     System capabilities: {capabilities}
#     INTRUCTIONS:
#     1. Decompose the problem into step-by-step plan
#     2. Each step should be a specific task that can be matched with a skill capability
#     3. If there is a 'Reflection' from previous failed attempts, adjust the plan to avoid those mistakes.
#     4. Output ONLY a JSON object with the key 'plan' containing a list of strings
#     """
#     user_prompt = f"""
#     CONTEXT:
#     Code: {state.user_context['code']}
#     Error: {state.user_context['stacktrace']}
#     Request: {state.user_context['message']}
#     PREVIOUS REFLECTION:
#     {state.reflection}
#     """
#     response = model_client.call(system_prompt, user_prompt) #TODOS: xem lai interface cua model_client
    
#     try:
#         plan_data = json.loads(response)
#         state.plan = plan_data.get("plan", [])
#         state.current_step_idx = 0
#     except Exception as e:
#         state.plan = ["Manual analysis required due to planning errpr: " + str(e)]
        
#     return state

# backend/services/skill_testing/core/plan_node.py

import json
from services.skill_testing.state import AgentState

from .skill_manager import SkillManager
from .registry import semantic_registry

def plan_node(state: AgentState, model_client):
    available_skills = semantic_registry.all_skills()
    capabilities = SkillManager.get_capabilities(available_skills)
    
    system_prompt = f"""
    You are an expert Software Engineer AI, Your goal is to solve the user's software engineering problem by breaking it down into smaller tasks and assigning them to the appropriate skills.
     System capabilities: {capabilities}
     INTRUCTIONS:
     1. Decompose the problem into step-by-step plan
     2. Each step should be a specific task that can be matched with a skill capability
     3. If there is a 'Reflection' from previous failed attempts, adjust the plan to avoid those mistakes.
     4. Output ONLY a JSON object with the key 'plan' containing a list of strings
     """
    user_prompt = f"""
    CONTEXT:
    Code: {state.user_context['code']}
    Error: {state.user_context['stacktrace']}
    Request: {state.user_context['message']}
    PREVIOUS REFLECTION:
    {state.reflection}
    """
    response = model_client.call(system_prompt, user_prompt) #TODOS: xem lai interface cua model_client
    
    try:
        plan_data = json.loads(response)
        state.plan = plan_data.get("plan", [])
        state.current_step_idx = 0
    except Exception as e:
        state.plan = ["Manual analysis required due to planning errpr: " + str(e)]
    return state