import time
from typing import Any, Callable, Optional
from ..storage.base import ExecutionRecord
from ..observer.performance_observer import PerformanceObserver

class CASSSkillProxy:
    """
    Standard Proxy wrapper for executing a Skill.
    Instruments the call with telemetry (latency, success/fail tracking).
    """
    def __init__(self, skill_func: Callable, session_id: str, observer: PerformanceObserver):
        self.skill_func = skill_func
        self.session_id = session_id
        self.observer = observer
        if hasattr(skill_func, "name"):
            self.skill_name = skill_func.name
        else:
            self.skill_name = getattr(skill_func, "__name__", "unknown-skill").replace("_", "-")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Executes the wrapped skill and records performance."""
        start_time = time.perf_counter()
        success = False
        error_msg = None
        result = None

        try:
            # 1. Execute the actual skill logic
            result = self.skill_func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            # 2. Capture and store the error message
            error_msg = str(e)
            success = False
            raise e
        finally:
            # 3. Calculate latency and report telemetry
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            record = ExecutionRecord(
                session_id=self.session_id,
                skill_name=self.skill_name,
                latency_ms=duration_ms,
                cost=0.0, # Logic for cost calculation can be added later
                success=success,
                error_message=error_msg
            )
            
            # 4. Trigger the feedback loop through the observer
            self.observer.report_execution(record)

    def invoke(self, input_data: Any) -> Any:
        """Executes the wrapped skill via invoke and records performance."""
        start_time = time.perf_counter()
        success = False
        error_msg = None
        result = None

        try:
            if hasattr(self.skill_func, "invoke"):
                result = self.skill_func.invoke(input_data)
            elif isinstance(input_data, dict):
                result = self.skill_func(**input_data)
            else:
                result = self.skill_func(input_data)
            success = True
            return result
        except Exception as e:
            error_msg = str(e)
            success = False
            raise e
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            record = ExecutionRecord(
                session_id=self.session_id,
                skill_name=self.skill_name,
                latency_ms=duration_ms,
                cost=0.0,
                success=success,
                error_message=error_msg
            )
            self.observer.report_execution(record)