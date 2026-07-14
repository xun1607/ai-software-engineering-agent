import json
import time
from typing import Dict, Any

from services.skill_testing.state import AgentState
from services.skill_testing.core.execution_models import RuntimeConfig, ExecutionResult
from services.skill_testing.core.skill_loader import SkillLoader
from services.skill_testing.core.parameter_resolver import resolve_parameters
from services.skill_testing.core.execution_runtime import ExecutionRuntime
from services.skill_testing.core.validation_runtime import ValidationRuntime
from services.skill_testing.core.telemetry_logger import TelemetryLogger

# Khởi tạo Validation Runtime đọc cấu hình từ overlay json
validation_runtime = ValidationRuntime()

async def llm_simulate_compiler(model_client, code: str, filename: str) -> dict:
    """Wrapper tương thích ngược để chạy Simulated Compiler qua LLMValidator plugin."""
    from services.skill_testing.core.validation_runtime import LLMValidator
    validator = LLMValidator()
    return await validator.validate(
        filename=filename,
        rel_path=filename,
        workspace_dir="",
        args={"patched_code": code},
        model_client=model_client
    )

async def execute_node(state: AgentState, model_client, skill_client) -> AgentState:
    """
    Node thực thi (Executor) đóng vai trò Orchestrator tinh giản:
    1. Skill Loader: Tải SOP kỹ năng từ Registry.
    2. Parameter Resolver: Giải quyết tham số (local + LLM fallback), tạo ra ExecutionRequest.
    3. Execution Runtime: Chạy kỹ năng vật lý, trả về ExecutionResult.
    4. Validation Runtime: Biên dịch/chạy thử mã nguồn, trả về ValidationReport.
    5. Telemetry Logger: Lưu vết lịch sử và ghi số liệu SQLite.
    """
    node_start_time = time.time()
    skill_name = state.selected_skill
    state.step_count += 1
    print(f"\n🚀 [EXECUTE NODE] -> Đang kích hoạt kỹ năng: '{skill_name}' (Bước tổng thể: {state.step_count})")
    
    # Khởi tạo Runtime Config (đọc ghi đè policy từ context nếu có)
    policy = state.user_context.get("validation_policy", "prefer_physical")
    runtime_config = RuntimeConfig(
        validation_policy=policy,
        timeout=30,
        llm_model="gpt-4o-mini"
    )
    
    # 1. Load skill information
    skill_info = await SkillLoader.load(skill_name)
    if not skill_info:
        state.last_observation = json.dumps({"status": "FAILED", "message": "Thiếu dữ liệu SOP"})
        return state
        
    # 2. Local parameter resolution + LLM Fallback -> ExecutionRequest
    request, resolved_args, usage, llm_latency_ms = await resolve_parameters(
        state, skill_info, skill_name, model_client, runtime_config
    )
    
    state.last_thought = f"Resolved arguments for {skill_name}: {request.args}"
    print(f"💡 [AGENT THOUGHT] -> Tham số cuối cùng cho '{skill_name}': {request.args}")
    
    # 3. Execute physical action -> ExecutionResult
    execution_result = None
    try:
        execution_result = await ExecutionRuntime.execute(skill_client, request)
        state.last_observation = json.dumps(execution_result.to_dict(), ensure_ascii=False)
        print(f"📦 [OBSERVATION] -> Kết quả thô từ hệ thống: {state.last_observation}")
    except Exception as e:
        execution_result = ExecutionResult(
            status="FAILED",
            stdout="",
            stderr=str(e),
            message="Gãy định dạng JSON"
        )
        state.last_observation = json.dumps(execution_result.to_dict(), ensure_ascii=False)
        print(f"❌ [SYSTEM ERROR] -> Quá trình thực thi kỹ năng bị gián đoạn: {str(e)}")
        
    # 4. Environment Validation -> ValidationReport
    validation_report = None
    if execution_result.status == "SUCCESS":
        validation_report = await validation_runtime.validate(
            skill_name=skill_name,
            args=request.args,
            workspace_dir=skill_client.workspace_dir,
            skill_client_class_name=skill_client.__class__.__name__,
            model_client=model_client,
            runtime_config=runtime_config
        )
        
    if validation_report:
        state.user_context["validation_feedback"] = validation_report.to_dict()
        if validation_report.exit_code != 0:
            # Ghi đè last_observation bằng thông tin lỗi biên dịch cụ thể
            state.last_observation = json.dumps({
                "status": "FAILED",
                "stdout": validation_report.stdout,
                "stderr": validation_report.stderr,
                "message": f"Environment validation failed (exit code {validation_report.exit_code}): {validation_report.stderr}"
            })
            print(f"❌ [ENVIRONMENT VALIDATOR] Thất bại! Feedback lỗi: {validation_report.stderr.strip()}")
        else:
            state.last_observation = json.dumps({
                "status": "SUCCESS",
                "stdout": validation_report.stdout,
                "message": "Environment validation passed."
            })
            print(f"✅ [ENVIRONMENT VALIDATOR] Thành công!")
    else:
        state.user_context.pop("validation_feedback", None)
        
    # 5. Log Telemetry
    node_latency_ms = int((time.time() - node_start_time) * 1000)
    TelemetryLogger.log(
        state=state,
        skill_name=skill_name,
        usage=usage,
        node_latency_ms=node_latency_ms,
        llm_latency_ms=llm_latency_ms,
        validation_report=validation_report
    )
    
    return state
