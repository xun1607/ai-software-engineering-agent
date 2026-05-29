import json
from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry

async def execute_node(state: AgentState, model_client, skill_client):
    """
    Node thuc thi: 
    1. Lay schema cua skill tu RAM Cache.
    2. Dung LLM de boc tach tham so tu context.
    3. Goi API thuc thi skill.
    """
    skill_name = state.selected_skill
    skill_info = semantic_registry.get_skill_by_name(skill_name)
    
    if not skill_info:
        state.last_observation = f"Error: Skill '{skill_name}' not found in cache."
        return state

    input_schema = skill_info.metadata.get("input", {})
    
    system_prompt = f"""
    You are a Parameter Extractor. Your task is to extract arguments for the skill '{skill_name}' 
    based on its JSON Schema and the provided user context.
    SKILL INPUT SCHEMA:
    {json.dumps(input_schema, indent=2)}
    INSTRUCTIONS:
    - Look at the code, error, and message in the context.
    - Extract exact values for each required field in the schema.
    - Output ONLY a JSON object containing the arguments.
    """
    
    user_prompt = f"""
    USER CONTEXT:
    Code: {state.user_context['code']}
    Error: {state.user_context['stacktrace']}
    Message: {state.user_context['message']}
    """
    
    
    arg_response = model_client.call(system_prompt, user_prompt)
    
    try:
        args = json.loads(arg_response)
        state.last_thought = f"Extracted arguments for {skill_name}: {args}"
        
        print(f"DEBUG: Executing skill {skill_name} (ID: {skill_info.id}) via API...")
        
        # Gia su skill_client la BackendClient ma chung ta da ban o cac cau truoc
        execution_result = await skill_client.execute_skill(skill_info.id, args)
        
        # Luu ket qua vao observation
        state.last_observation = json.dumps(execution_result)
        
    except Exception as e:
        state.last_observation = f"Execution failed: {str(e)}"
        
    state.history.append({
        "step": state.current_step_idx,
        "task": state.current_task,
        "skill": skill_name,
        "observation": state.last_observation
    })
    
    return state