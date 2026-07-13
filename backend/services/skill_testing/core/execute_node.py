import json
import time
from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry
from shared.db import get_session
from services.skill_testing.models import AgentExecutionLog

async def execute_node(state: AgentState, model_client, skill_client):
    """
    Node thực thi (Executor): 
    1. Xác thực tên kỹ năng dạng chuỗi (str) từ Registry.
    2. Dùng LLM bóc tách tham số đầu vào tương ứng dựa theo ngữ cảnh lỗi của User.
    3. Gọi API thực thi kỹ năng ngầm và lưu kết quả.
    """
    node_start_time = time.time()
    skill_name = state.selected_skill
    state.step_count += 1
    print(f"\n🚀 [EXECUTE NODE] -> Đang kích hoạt kỹ năng: '{skill_name}' (Bước tổng thể: {state.step_count})")
    
    # Tải chi tiết kỹ năng qua Lazy Load (TASK_2A)
    skill_info = await semantic_registry.get_skill_detail(skill_name)
    
    if not skill_info:
        state.last_observation = json.dumps({"status": "FAILED", "message": "Thiếu dữ liệu SOP"})
        return state
    
    metadata = skill_info.get("metadata", {}) or skill_info
    input_schema = metadata.get("input", {}) or skill_info.get("input", {})
    output_schema = metadata.get("output", {}) or skill_info.get("output", {})

    # 2. Thiết lập Prompt tối giản chỉ dựa trên JSON Schema (TASK_5A)
    system_prompt = f"""
    You are a Software Engineering Parameter Extractor and Code Generator for the skill: '{skill_name}'.
    Your job is to look at the user's code context, error log, and request to generate the arguments matching the JSON schemas below.
    
    INPUT SCHEMA:
    {json.dumps(input_schema or {"patched_code": {"type": "string", "description": "The complete patched source code content. MUST contain the full code, enclosing class, imports, methods, etc."}, "file": {"type": "string"}}, ensure_ascii=False, indent=2)}
    
    OUTPUT SCHEMA:
    {json.dumps(output_schema, ensure_ascii=False, indent=2)}
    
    EXPECTED ARGUMENTS LOGIC BASED ON SKILL NAME:
    - If skill is 'analyze-stacktrace' or 'debug-java-null-pointer': extract 'stacktrace' and 'file' (or 'source_path').
    - If skill is 'read-code-context': extract 'file' and 'line' (as integer).
    - If skill is 'suggest-java-fix' or 'suggest-python-fix': extract 'file' (the name of the file being fixed) and generate the ENTIRE completely patched source code file, returning it inside the 'patched_code' field. You MUST return the FULL completed source code. DO NOT use comments like '// ... rest of code' or placeholders. If you do, the workspace compilation will fail.
    
    INSTRUCTIONS:
    1. Generate a flat JSON object containing only the key-value pairs of extracted/generated parameters matching the Input Schema (specifically generate the 'patched_code' field for code fixes).
    2. Do NOT add any extra conversational text. Output ONLY valid JSON.
    """
    
    user_prompt = f"""
    USER CONTEXT TO EXTRACT FROM:
    - File Name: {state.user_context.get('filename', '')}
    - Source Code: {state.user_context.get('code', '')}
    - Stacktrace/Error: {state.user_context.get('stacktrace', '')}
    - User Message: {state.user_context.get('message', '')}
    """
    
    start_time = time.time()
    
    # Thử bóc tách chỉ sử dụng Schema
    arg_response = None
    args = {}
    try:
        arg_response = await model_client.call(system_prompt, user_prompt)
        args = json.loads(arg_response)
    except Exception as e:
        print(f"⚠️ [EXECUTE NODE] Schema-only extraction failed: {e}. Fallback to full instructions.")
        # Phục hồi lỗi: Tải instructions đầy đủ (TASK_5A Fallback)
        raw_instructions = skill_info.get("raw_content") or skill_info.get("description") or ""
        system_prompt_fallback = system_prompt + f"\n\nFULL SKILL INSTRUCTIONS:\n{raw_instructions}"
        try:
            arg_response = await model_client.call(system_prompt_fallback, user_prompt)
            args = json.loads(arg_response)
        except Exception as ex:
            print(f"❌ [EXECUTE NODE] Fallback extraction failed: {ex}")
            args = {}
            
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Sync và log tokens/latency 
    usage = getattr(model_client, "last_call_usage", None) or {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "model": "gpt-4o-mini",
        "cost": 0.0
    }
    
    history_entry = {
        "node": "execute_node",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "latency_ms": latency_ms,
        "model": usage.get("model", "gpt-4o-mini")
    }
    state.execution_history.append(history_entry)
    
    # Cộng dồn vào state
    state.prompt_tokens += usage.get("prompt_tokens", 0)
    state.completion_tokens += usage.get("completion_tokens", 0)
    state.total_tokens += usage.get("total_tokens", 0)
    state.total_cost += usage.get("cost", 0.0)
    
    try:
        state.last_thought = f"Extracted arguments for {skill_name}: {args}"
        print(f"💡 [AGENT THOUGHT] -> Tham số bóc tách thành công cho '{skill_name}': {args}")
        
        print(f"🤖 [SYSTEM ACTION] -> Bắn lệnh thực thi kỹ năng '{skill_name}' qua Client...")
        
        execution_result = await skill_client.execute_skill(skill_name, args)
        
        state.last_observation = json.dumps(execution_result, ensure_ascii=False)
        print(f"📦 [OBSERVATION] -> Kết quả thô từ hệ thống: {state.last_observation}")
        
    except Exception as e:
        state.last_observation = json.dumps({"status": "FAILED", "stdout": "", "stderr": str(e), "message": "Gãy định dạng JSON"}, ensure_ascii=False)
        print(f"❌ [SYSTEM ERROR] -> Quá trình thực thi kỹ năng bị gián đoạn: {str(e)}")
        
    state.history.append({
        "step": state.current_step_idx,
        "task": state.current_task,
        "skill": skill_name,
        "observation": state.last_observation
    })
    
    # Ghi log thực thi vào SQLite cho Task 4
    try:
        node_latency_ms = int((time.time() - node_start_time) * 1000)
        task_id = state.user_context.get("task_id", "unknown_task")
        task_type = state.user_context.get("task_type", "unknown_type")
        baseline_mode = state.user_context.get("baseline_mode", "unknown_baseline")
        
        with get_session() as session:
            log_entry = AgentExecutionLog(
                task_id=task_id,
                task_type=task_type,
                skill_name=skill_name,
                baseline_mode=baseline_mode,
                success=False,  # Placeholder, sẽ được cập nhật sau khi đánh giá kết quả vật lý
                quality=0.0,    # Placeholder, sẽ được cập nhật sau khi đánh giá chất lượng
                latency_ms=node_latency_ms,
                total_tokens=usage.get("total_tokens", 0),
                cost=usage.get("cost", 0.0)
            )
            session.add(log_entry)
            print(f"💾 [DB LOG] Đã lưu log chạy bước này vào SQLite: {skill_name} | Task: {task_id} | Latency: {node_latency_ms}ms")
    except Exception as db_err:
        print(f"⚠️ [DB LOG ERROR] Lỗi khi ghi log thực thi vào SQLite: {db_err}")
        
    return state
