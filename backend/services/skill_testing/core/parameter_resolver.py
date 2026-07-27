import re
import json
import time
from typing import List, Dict, Any, Tuple

from services.skill_testing.state import AgentState
from services.skill_testing.core.execution_models import ExecutionRequest, RuntimeConfig

def clean_and_parse_json(raw_str: str) -> dict:
    """
    Cleans raw markdown JSON blocks if present, cleans trailing commas,
    and parses into a Python dictionary.
    """
    cleaned = raw_str.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
            
    cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"⚠️ [JSON PARSER] Parsing failed. Raw string: {raw_str}. Error: {e}")
        return {}

class ParameterResolver:
    """
    ParameterResolver:
    Nhiệm vụ: tìm và điền các tham số đầu vào cần thiết trước khi phải nhờ đến LLM.
    Giúp hệ thống giảm số lần gọi LLM, giúp tiết kiệm token và phản hồi nhanh hơn
    """
    def __init__(self, user_context: Dict[str, Any]):
        self.user_context = user_context or {}
        
    def resolve_by_rules(self, required_params: List[str]) -> Dict[str, Any]:
        resolved = {}
        mappings = {
            "file": ["filename", "file_path", "file"],
            "source_path": ["filename", "file_path", "file"],
            "code": ["code", "source_code", "content"],
            "source_code": ["code", "source_code", "content"],
            "stacktrace": ["stacktrace", "error", "error_log"],
            "error_message": ["stacktrace", "error", "error_log", "message"]
        }
        
        for param in required_params:
            if param in mappings:
                for context_key in mappings[param]:
                    if context_key in self.user_context and self.user_context[context_key]:
                        resolved[param] = self.user_context[context_key]
                        break
                        
        return resolved

    def resolve_by_parsing(self, required_params: List[str]) -> Dict[str, Any]:
        resolved = {}
        stacktrace = self.user_context.get("stacktrace") or ""
        message = self.user_context.get("message") or ""
        
        if "line" in required_params or "line_number" in required_params:
            target_key = "line" if "line" in required_params else "line_number"
            line_val = None
            
            # Pattern 1: Java stacktrace (e.g., LoginService.java:42)
            java_match = re.search(r"\.java:(\d+)", stacktrace)
            if java_match:
                line_val = int(java_match.group(1))
            else:
                # Pattern 2: Python traceback (e.g., File "app.py", line 15)
                py_match = re.search(r"line\s+(\d+)", stacktrace, re.IGNORECASE)
                if py_match:
                    line_val = int(py_match.group(1))
                else:
                    # Pattern 3: User message containing a line number (e.g., "lỗi ở dòng 12")
                    msg_match = re.search(r"(?:dòng|line)\s+(\d+)", message, re.IGNORECASE)
                    if msg_match:
                        line_val = int(msg_match.group(1))
            
            if line_val is not None:
                resolved[target_key] = line_val
                
        return resolved

    def resolve(self, required_params: List[str]) -> tuple[Dict[str, Any], List[str]]:
        # Step 1: Try Rule-Based
        resolved_args = self.resolve_by_rules(required_params)
        
        # Step 2: Identify missing parameters and try Regex Parsing
        missing_params = [p for p in required_params if p not in resolved_args]
        if missing_params:
            parsed_args = self.resolve_by_parsing(missing_params)
            resolved_args.update(parsed_args)
            
        # Step 3: Re-evaluate missing parameters
        still_missing = [p for p in required_params if p not in resolved_args]
        
        return resolved_args, still_missing

def build_prompts(skill_name: str, skill_info: dict, state: AgentState) -> tuple[str, str]:
    metadata = skill_info.get("metadata", {}) or skill_info
    input_schema = metadata.get("input", {}) or skill_info.get("input", {})
    output_schema = metadata.get("output", {}) or skill_info.get("output", {})
    
    properties = input_schema.get("properties", {})
    dynamic_instructions = []
    for param_name, param_info in properties.items():
        param_type = param_info.get("type", "string")
        param_desc = param_info.get("description", "")
        dynamic_instructions.append(f"- '{param_name}' ({param_type}): {param_desc}")
    dynamic_instructions_str = "\n    ".join(dynamic_instructions) if dynamic_instructions else "- No inputs required."
    
    system_prompt = f"""
    You are a Software Engineering Parameter Extractor and Code Generator for the skill: '{skill_name}'.
    Your job is to look at the user's code context, error log, and request to generate the arguments matching the JSON schemas below.
    
    REQUIRED INPUT PROPERTIES:
    {dynamic_instructions_str}
    
    INPUT SCHEMA:
    {json.dumps(input_schema or {"patched_code": {"type": "string", "description": "The complete patched source code content. MUST contain the full code, enclosing class, imports, methods, etc."}, "file": {"type": "string"}}, ensure_ascii=False, indent=2)}
    
    OUTPUT SCHEMA:
    {json.dumps(output_schema, ensure_ascii=False, indent=2)}
    
    EXPECTED ARGUMENTS LOGIC BASED ON SKILL NAME:
    -If the parameter 'patched_code' is required: generate the patched code content.
    CRITICAL RULE: Match the structure of the input source code. 
      If the input source code is a short snippet, ONLY output the corrected snippet. 
      Ensure variable declarations maintain their original scope so that they are accessible by subsequent statements in the snippet (e.g., do not declare critical variables inside local if-blocks if they are used later).
      Do NOT add class wrappers, packages, or imports unless they were already present in the input source code. 
      If the input source code is a full class/file, then output the entire full class/file. 
      DO NOT use comments like '// ... rest of code' or placeholders.
    
    INSTRUCTIONS:
    1. Generate a flat JSON object containing only the key-value pairs of extracted/generated parameters matching the Input Schema.
    2. Do NOT add any extra conversational text. Output ONLY valid JSON.
    """
    
    user_prompt = f"""
    USER CONTEXT TO EXTRACT FROM:
    - File Name: {state.user_context.get('filename', '')}
    - Source Code: {state.user_context.get('code', '')}
    - Stacktrace/Error: {state.user_context.get('stacktrace', '')}
    - User Message: {state.user_context.get('message', '')}
    """
    
    return system_prompt, user_prompt

async def extract_arguments(model_client, system_prompt: str, user_prompt: str, skill_info: dict, skill_name: str) -> tuple[dict, int]:
    start_time = time.time()
    args = {}
    try:
        arg_response = await model_client.call(system_prompt, user_prompt)
        args = clean_and_parse_json(arg_response)
    except Exception as e:
        print(f"⚠️ [EXECUTE NODE] Schema-only extraction failed: {e}. Fallback to full instructions.")
        raw_instructions = skill_info.get("raw_content") or skill_info.get("description") or ""
        system_prompt_fallback = system_prompt + f"\n\nFULL SKILL INSTRUCTIONS:\n{raw_instructions}"
        try:
            arg_response = await model_client.call(system_prompt_fallback, user_prompt)
            args = clean_and_parse_json(arg_response)
        except Exception as ex:
            print(f"❌ [EXECUTE NODE] Fallback extraction failed: {ex}")
            args = {}
            
    latency_ms = int((time.time() - start_time) * 1000)
    return args, latency_ms

async def resolve_parameters(
    state: AgentState,
    skill_info: dict,
    skill_name: str,
    model_client,
    runtime_config: RuntimeConfig
) -> tuple[ExecutionRequest, dict, dict, int]:
    """
    Điều phối phân giải tham số (Parameter Resolver Orchestrator):
    1. Giải quyết tham số cục bộ bằng ParameterResolver.
    2. Nếu còn thiếu, gọi LLM điền nốt tham số.
    3. Trả về ExecutionRequest cùng thông tin đo lường token và latency.
    """
    metadata = skill_info.get("metadata", {}) or skill_info
    input_schema = metadata.get("input", {}) or skill_info.get("input", {})
    required_params = list(input_schema.get("properties", {}).keys())

    resolver = ParameterResolver(state.user_context)
    resolved_args, missing_params = resolver.resolve(required_params)
    
    args = resolved_args.copy()
    llm_latency_ms = 0
    usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "model": "local_resolver",
        "cost": 0.0
    }
    
    if missing_params:
        print(f"🧩 [RESOLVER] Trích xuất local thành công: {resolved_args}. Còn thiếu {missing_params}. Gọi LLM Fallback...")
        sys_prompt, usr_prompt = build_prompts(skill_name, skill_info, state)
        llm_args, llm_latency_ms = await extract_arguments(model_client, sys_prompt, usr_prompt, skill_info, skill_name)
        
        for param in missing_params:
            if param in llm_args:
                args[param] = llm_args[param]
                
        usage = getattr(model_client, "last_call_usage", None) or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": runtime_config.llm_model,
            "cost": 0.0
        }
    else:
        print(f"🚀 [RESOLVER] Đã giải quyết THÀNH CÔNG toàn bộ tham số tại local: {args}")
        
    return ExecutionRequest(skill_name, args), resolved_args, usage, llm_latency_ms
