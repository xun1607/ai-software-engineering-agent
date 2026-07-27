import json
import time
from services.skill_testing.state import AgentState
from .registry import semantic_registry

async def plan_node(state: AgentState, model_client):
    print("--- [Planning Node] Generating plan based on user context and available skills ---")
    
    capabilities = semantic_registry.capabilities_manifest
    
    system_prompt = f"""
    You are the Lead Software Architect AI. Your job is to analyze a software issue and generate a sequential plan to fix it.
    CRITICAL RULE:
    You must ONLY use the exact tool names listed in the AVAILABLE TOOLS catalog below to build your plan.
    Do NOT create custom text, instructions, or sub-steps like 'check_user_object_for_null'. 
    Every element in your plan list MUST match one of the available tool names perfectly.
    AVAILABLE TOOLS CATALOG FROM AG1 REGISTRY:
        {capabilities}
    Output a valid JSON object containing exactly one field 'plan', which is a list of strings representing the selected tool names in order.
    Example: {{"plan": ["analyze-stacktrace", "suggest-java-fix", "debug-java-null-pointer"]}}
    """
    user_prompt = f"""
    CONTEXT:
    File Name: {state.user_context.get('filename', '')}
    Code: {state.user_context.get('code', '')}
    Error: {state.user_context.get('stacktrace', '')}
    Request: {state.user_context.get('message', '')}
    PREVIOUS REFLECTION (IF ANY):
    {state.reflection}
    """
    
    start_time = time.time()
    response = await model_client.call(system_prompt, user_prompt)
    latency_ms = int((time.time() - start_time) * 1000)
    
    usage = getattr(model_client, "last_call_usage", None) or {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "model": "gpt-4o-mini",
        "cost": 0.0
    }
    
    history_entry = {
        "node": "plan_node",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "latency_ms": latency_ms,
        "model": usage.get("model", "gpt-4o-mini")
    }
    state.execution_history.append(history_entry)
    
    state.prompt_tokens += usage.get("prompt_tokens", 0)
    state.completion_tokens += usage.get("completion_tokens", 0)
    state.total_tokens += usage.get("total_tokens", 0)
    state.total_cost += usage.get("cost", 0.0)
    
    if not state.goal:
        state.goal = state.user_context.get('message')
        
    try:
        plan_data = json.loads(response)
        state.plan = plan_data.get("plan", [])
        state.current_step_idx = 0
        print(f"📝 [PLANNER LOG] Kế hoạch được thiết lập thành công: {state.plan}")
    except Exception as e:
        print(f"⚠️ [PLANNER ERROR] Không thể phân tích JSON từ LLM. Kích hoạt fallback thủ công. Lỗi: {e}")
        state.plan = ["Manual_analysis_fallback_task"]
        state.current_step_idx = 0
    return state