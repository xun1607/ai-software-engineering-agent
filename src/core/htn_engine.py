from typing import Any, Dict, List, Set

from models.task import Task


def htn_recursive_decompose(
    recipe_id: str,
    lookup_table: Dict[str, Dict[str, Any]],
    visited: Set[str] | None = None,
) -> List[dict]:
    """Recursively decompose a recipe into primitive tasks."""
    visited = visited or set()
    if recipe_id in visited:
        raise ValueError(f"Cyclic HTN recipe dependency detected: {recipe_id}")

    recipe = lookup_table.get(recipe_id)
    if not recipe:
        return []

    visited.add(recipe_id)

    if recipe.get("type") == "primitive":
        visited.remove(recipe_id)
        return [Task.from_recipe(recipe_id, recipe).to_dict()]

    primitive_tasks: List[dict] = []
    for sub_id in recipe.get("subtasks", []):
        primitive_tasks.extend(htn_recursive_decompose(sub_id, lookup_table, visited))

    visited.remove(recipe_id)
    return primitive_tasks
