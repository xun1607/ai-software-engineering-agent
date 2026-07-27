import uuid
import time
import json
from typing import Dict, Any, Optional

from services.skill_testing.state import AgentState
from services.skill_testing.core.execution_models import ValidationReport
from shared.db import get_session
from services.skill_testing.models import AgentExecutionLog

class TelemetryLogger:
    """Telemetry Logger: Lưu trữ vết thực thi vào LangGraph State và SQLite Database."""
    
    @staticmethod
    def log_to_db(
        state: AgentState,
        skill_name: str,
        usage: dict,
        node_latency_ms: int,
        report: Optional[ValidationReport] = None
    ) -> Optional[str]:
        try:
            task_id = state.user_context.get("task_id", "unknown_task")
            task_type = state.user_context.get("task_type", "unknown_type")
            baseline_mode = state.user_context.get("baseline_mode", "unknown_baseline")
            
            log_id = str(uuid.uuid4())
            
            with get_session() as session:
                log_entry = AgentExecutionLog(
                    id=log_id,
                    task_id=task_id,
                    task_type=task_type,
                    skill_name=skill_name,
                    baseline_mode=baseline_mode,
                    success=False,  # Sẽ được cập nhật chính xác tại evaluate_node
                    quality=0.0,    # Sẽ được cập nhật chính xác tại evaluate_node
                    latency_ms=node_latency_ms,
                    total_tokens=usage.get("total_tokens", 0),
                    cost=usage.get("cost", 0.0),
                    
                    # Validation report columns
                    validator_name=report.validator_name if report else None,
                    validator_type=report.validator_type if report else None,
                    validator_latency_ms=report.latency_ms if report else None,
                    exit_code=report.exit_code if report else None,
                    validation_feedback=report.stderr if report else None
                )
                session.add(log_entry)
                print(f"💾 [DB LOG] Đã lưu log chạy bước này vào SQLite: {skill_name} | Latency: {node_latency_ms}ms | log ID: {log_id}")
                if report:
                    print(f"   └─ [VALIDATOR TELEMETRY] Exit code: {report.exit_code} | Type: {report.validator_type} | Latency: {report.latency_ms}ms")
                return log_id
        except Exception as db_err:
            print(f"⚠️ [DB LOG ERROR] Lỗi khi ghi log thực thi vào SQLite: {db_err}")
            return None

    @classmethod
    def log(
        cls,
        state: AgentState,
        skill_name: str,
        usage: dict,
        node_latency_ms: int,
        llm_latency_ms: int,
        validation_report: Optional[ValidationReport] = None
    ):
        # 1. Update LangGraph State stats
        history_entry = {
            "node": "execute_node",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": llm_latency_ms,
            "model": usage.get("model", "local_resolver")
        }
        state.execution_history.append(history_entry)
        
        state.prompt_tokens += usage.get("prompt_tokens", 0)
        state.completion_tokens += usage.get("completion_tokens", 0)
        state.total_tokens += usage.get("total_tokens", 0)
        state.total_cost += usage.get("cost", 0.0)
        
        # 2. Update execution history
        state.history.append({
            "step": state.current_step_idx,
            "task": state.current_task,
            "skill": skill_name,
            "observation": state.last_observation
        })
        
        # 3. DB log
        log_id = cls.log_to_db(state, skill_name, usage, node_latency_ms, validation_report)
        if log_id:
            state.user_context["last_log_id"] = log_id
