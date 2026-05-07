from __future__ import annotations

from typing import Any, Dict, Optional

from core.metrics import initial_metrics
from core.state import AgentState


MAX_TASK_RETRIES = 2


def evaluate_result(task: Dict[str, Any], output: Any, error: Optional[str] = None) -> Dict[str, Any]:
    """Quick execution-level evaluation used by the executor result record."""
    passed, reason = _validate_task_output(task, output, error)
    return {
        "success": passed,
        "retryable": not passed,
        "score": 1.0 if passed else 0.0,
        "reason": "completed" if passed else reason,
        "task_id": task.get("id"),
    }


def evaluator_node(state: AgentState):
    """Quality gate after executor: retry current task or advance the plan cursor."""
    scheduler = state.get("scheduler", {})
    step_idx = scheduler.get("current_step", 0)
    tasks = state.get("plan", {}).get("tasks", [])
    if step_idx >= len(tasks):
        return {
            "status": "completed",
            "scheduler": {**scheduler, "next_action": "end"},
        }

    task = tasks[step_idx]
    task_id = task.get("id")
    task_result = state.get("context_memory", {}).get("task_results", {}).get(task_id, {})
    output = task_result.get("output")
    error = task_result.get("error")
    passed, reason = _validate_task_output(task, output, error)

    if not passed:
        retry_count = state.get("retry_count", 0) + 1
        metrics = initial_metrics(state.get("metrics", {}))
        metrics["total_retries"] += 1
        if retry_count <= MAX_TASK_RETRIES:
            print(f"[Evaluator] Task failed, retrying ({retry_count}/{MAX_TASK_RETRIES})...")
            return {
                "status": "running",
                "retry_count": retry_count,
                "last_error": reason,
                "metrics": metrics,
                "scheduler": {
                    **scheduler,
                    "current_step": step_idx,
                    "next_action": "retry",
                    "replan_reason": reason,
                },
            }

        if not state.get("is_replanned", False):
            print("[Evaluator] Retry budget exhausted, replanning once...")
            metrics["replan_count"] += 1
            return {
                "status": "replanning",
                "retry_count": 0,
                "last_error": reason,
                "metrics": metrics,
                "is_replanned": True,
                "scheduler": {
                    **scheduler,
                    "current_step": step_idx,
                    "next_action": "replan",
                    "replan_reason": reason,
                },
            }

        print(f"[Evaluator] Task failed after {MAX_TASK_RETRIES} retries, continuing...")
        next_step = step_idx + 1
        return {
            "status": "completed" if next_step >= len(tasks) else "running",
            "retry_count": 0,
            "last_error": reason,
            "metrics": metrics,
            "scheduler": {
                **scheduler,
                "current_step": next_step,
                "next_action": "end" if next_step >= len(tasks) else "continue",
                "replan_reason": reason,
            },
        }

    next_step = step_idx + 1
    print("[Evaluator] Task passed.")
    return {
        "status": "completed" if next_step >= len(tasks) else "running",
        "retry_count": 0,
        "last_error": "",
        "scheduler": {
            **scheduler,
            "current_step": next_step,
            "next_action": "end" if next_step >= len(tasks) else "continue",
            "replan_reason": None,
        },
    }


def route_after_evaluator(state: AgentState) -> str:
    action = state.get("scheduler", {}).get("next_action")
    if action == "retry":
        return "retry"
    if action == "replan":
        return "replan"
    if action == "continue":
        return "continue"
    return "end"


def _validate_task_output(task: Dict[str, Any], output: Any, error: Optional[str] = None) -> tuple[bool, str]:
    if error:
        return False, str(error)
    if _empty(output):
        return False, "output is empty"
    if _contains_error(output):
        return False, "output contains error"

    for key in task.get("expected_outputs", []):
        if not isinstance(output, dict):
            return False, f"output is not an object; expected key '{key}'"
        if key not in output:
            return False, f"missing expected output key: {key}"
        if _empty(output.get(key)):
            return False, f"expected output key is empty: {key}"

    return True, "ok"


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _contains_error(value: Any) -> bool:
    return "error" in str(value).lower()
