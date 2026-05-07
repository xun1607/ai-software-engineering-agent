from core.recipe_loader import load_recipes
from core.htn_engine import htn_recursive_decompose


def planner_node(state):
    recipes = load_recipes()
    target_recipe = "unit_test_gen"
    plan = htn_recursive_decompose(target_recipe, recipes)
    print(f"[Planner] {len(plan)} tasks")

    return {
        "plan": plan,
        "current_step": 0
    }