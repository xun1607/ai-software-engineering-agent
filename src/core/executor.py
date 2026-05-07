from __future__ import annotations

from typing import Any, Dict

from core.evaluator import evaluate_result
from core.execution_bridge import ExecutionBridge
from core.metrics import add_token_usage, estimate_tokens, initial_metrics


bridge = ExecutionBridge()


def executor_node(state):
    """Execute the current task only; evaluator owns retry/advance decisions."""
    scheduler = state.get("scheduler", {})
    step_idx = scheduler.get("current_step", 0)
    tasks = state.get("plan", {}).get("tasks", [])
    if step_idx >= len(tasks):
        return {"status": "completed", "scheduler": {**scheduler, "next_action": "end"}}

    task = tasks[step_idx]
    print(f"[Executor] Step {step_idx + 1}/{len(tasks)} - {task.get('capability')}")
    if state.get("retry_count", 0) > 0:
        print(f"[Executor] Retry context: {state.get('last_error')}")

    prepared_input = _prepare_task_input(task, state)
    execution = bridge.execute(task, prepared_input)
    token_usage = execution.get("token_usage", 0)
    if token_usage == 0 and task.get("skill_id", "").startswith("llm"):
        token_usage = estimate_tokens(prepared_input) + estimate_tokens(execution.get("output"))
    evaluation = evaluate_result(task, execution.get("output"), execution.get("error"))

    result = {
        "task_id": task.get("id"),
        "skill_id": execution.get("skill_id"),
        "capability": task.get("capability"),
        "input": prepared_input,
        "output": execution.get("output"),
        "success": execution.get("success", False) and evaluation["success"],
        "error": execution.get("error"),
        "evaluation": evaluation,
        "token_usage": token_usage,
    }

    context_memory = _write_context_memory(state.get("context_memory", {}), task, result)
    artifacts = _write_artifacts(state.get("artifacts", {}), task, result)

    return {
        "results": [result],
        "context_memory": context_memory,
        "artifacts": artifacts,
        "metrics": add_token_usage(initial_metrics(state.get("metrics", {})), token_usage),
        "status": "running",
        "scheduler": {
            **scheduler,
            "current_step": step_idx,
            "next_action": "evaluate",
            "replan_reason": result["error"],
        },
        "errors": [result["error"]] if result["error"] else [],
    }


def _prepare_task_input(task: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    memory = state.get("context_memory", {})
    task_results = memory.get("task_results", {})
    dependency_outputs = {
        dependency_id: task_results.get(dependency_id, {}).get("output")
        for dependency_id in task.get("depends_on", [])
        if dependency_id in task_results
    }

    return {
        "user_input": state.get("input", ""),
        "task": task,
        "facts": memory.get("facts", {}),
        "dependency_outputs": dependency_outputs,
        "last_output": memory.get("last_output"),
        "artifacts": state.get("artifacts", {}),
        "retry_count": state.get("retry_count", 0),
        "last_error": state.get("last_error", ""),
        "retry_instruction": _retry_instruction(state),
    }


def _retry_instruction(state: Dict[str, Any]) -> str:
    if state.get("retry_count", 0) <= 0:
        return ""
    return f"The previous attempt failed with error: {state.get('last_error')}. Please fix it and provide a better result."


def _write_context_memory(memory: Dict[str, Any], task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    task_results = {
        **memory.get("task_results", {}),
        task.get("id"): result,
    }
    facts = {
        **memory.get("facts", {}),
        "last_task_id": task.get("id"),
        "last_skill_id": result.get("skill_id"),
    }

    return {
        **memory,
        "task_results": task_results,
        "facts": facts,
        "last_output": result.get("output"),
    }


def _write_artifacts(artifacts: Dict[str, Any], task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    output = result.get("output")
    if not isinstance(output, dict):
        return artifacts

    updated = dict(artifacts)
    for key in task.get("expected_outputs", []):
        if key in output:
            updated[key] = output[key]
    return updated
