from __future__ import annotations

from core.htn_engine import htn_recursive_decompose
from core.recipe_loader import load_recipes
from core.router import route_recipe
from models.task import Plan, Task


def planner_node(state):
    """Create a structured execution plan; do not execute skills here."""
    user_input = state.get("input", "")
    recipes = load_recipes()
    route = route_recipe(user_input, recipes)

    if route.matched and route.recipe_id:
        tasks = htn_recursive_decompose(route.recipe_id, recipes)
        strategy = "recipe_htn"
    else:
        tasks = [Task.from_user_goal(user_input)]
        strategy = "llm_fallback"

    plan = Plan(
        id=route.recipe_id or "fallback_plan",
        goal=user_input,
        tasks=tasks,
        strategy=strategy,
        route=route.to_dict(),
        status="running",
    )

    print(f"[Planner] strategy={strategy}, tasks={plan.task_count}")
    return {
        "plan": plan.to_dict(),
        "matched_recipe_id": route.recipe_id,
        "planning_strategy": strategy,
        "status": "running" if plan.task_count else "completed",
        "context_memory": {
            **state.get("context_memory", {}),
            "user_goal": user_input,
            "route_decision": route.to_dict(),
            "task_results": state.get("context_memory", {}).get("task_results", {}),
            "facts": state.get("context_memory", {}).get("facts", {}),
        },
        "artifacts": state.get("artifacts", {}),
        "scheduler": {
            **state.get("scheduler", {}),
            "current_step": 0,
            "retry_count": 0,
            "max_retries": state.get("scheduler", {}).get("max_retries", 1),
            "next_action": "continue" if plan.task_count else "end",
        },
        "errors": [],
    }
