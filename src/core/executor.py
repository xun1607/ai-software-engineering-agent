from __future__ import annotations
from core.state import AgentState
from typing import Any, Dict

from core.evaluator import evaluate_result
from core.execution_bridge import ExecutionBridge


bridge = ExecutionBridge()


def executor_node(state):
    """Prepare memory-backed input, execute one task through AG1, and store result."""
    scheduler = state.get("scheduler", {})
    step_idx = scheduler.get("current_step", 0)
    tasks = state.get("plan", {}).get("tasks", [])
    if step_idx >= len(tasks):
        return {"status": "completed", "scheduler": {**scheduler, "next_action": "end"}}

    task = tasks[step_idx]
    print(f"[Executor] Step {step_idx + 1}/{len(tasks)} - {task.get('capability')}")

    prepared_input = _prepare_task_input(task, state)
    execution = bridge.execute(task, prepared_input)
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
    }

    context_memory = _write_context_memory(state.get("context_memory", {}), task, result)
    artifacts = _write_artifacts(state.get("artifacts", {}), task, result)

    next_step = step_idx + 1
    failed = not result["success"]
    done = next_step >= len(tasks)
    next_action = "replan" if failed else "end" if done else "continue"

    return {
        "results": [result],
        "context_memory": context_memory,
        "artifacts": artifacts,
        "status": "failed" if failed else "completed" if done else "running",
        "scheduler": {
            **scheduler,
            "current_step": next_step,
            "next_action": next_action,
            "replan_reason": result["error"] if failed else None,
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
    }


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


print("\n--- [DEBUG STATE] ---")
print(f"Memory: {list(state['context_memory'].keys())}")
print(f"Artifacts: {list(state['artifacts'].keys())}")
print("----------------------\n")