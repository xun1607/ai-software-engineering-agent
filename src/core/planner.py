# from core.recipe_loader import load_recipes
# from core.htn_engine import htn_recursive_decompose

# # cần implement thêm logic cho planner, hiện tại là hardcode, sau này sẽ thay bằng router để chọn recipe phù hợp với input của user
# def planner_node(state):
#     recipes = load_recipes()
#     target_recipe = "unit_test_gen"  # sau này dựa vào input của user để chọn recipe phù hợp
#     plan = htn_recursive_decompose(target_recipe, recipes)
#     print(f"[Planner] {len(plan)} tasks")

#     return {
#         "plan": plan,
#         "current_step": 0
#     }

from __future__ import annotations

from core.htn_engine import htn_recursive_decompose
from core.recipe_loader import load_recipes
from core.router import route_recipe
from models.task import Task


def planner_node(state):
    """Create an execution plan; do not execute skills here."""
    user_input = state.get("input", "")
    recipes = load_recipes()
    match = route_recipe(user_input, recipes)

    if match.matched and match.recipe_id:
        plan = htn_recursive_decompose(match.recipe_id, recipes)
        strategy = "recipe_htn"
    else:
        plan = [Task.from_user_goal(user_input).to_dict()]
        strategy = "llm_fallback"

    print(f"[Planner] strategy={strategy}, tasks={len(plan)}")
    return {
        "plan": plan,
        "matched_recipe_id": match.recipe_id,
        "planning_strategy": strategy,
        "status": "running" if plan else "completed",
        "current_step": 0,
        "context_data": state.get("context_data", {}),
        "errors": [],
    }