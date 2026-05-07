import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


VALID_RECIPE_TYPES = {"composite", "primitive"}


def default_recipe_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "recipes.json"


@lru_cache(maxsize=4)
def load_recipes(path: str | None = None) -> Dict[str, Dict[str, Any]]:
    recipe_path = Path(path) if path else default_recipe_path()
    with recipe_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    recipes = {item["recipe_id"]: item for item in data}
    validate_recipes(recipes)
    return recipes


def validate_recipes(recipes: Dict[str, Dict[str, Any]]) -> None:
    for recipe_id, recipe in recipes.items():
        recipe_type = recipe.get("type")
        if recipe_type not in VALID_RECIPE_TYPES:
            raise ValueError(f"Recipe {recipe_id} has invalid type: {recipe_type}")

        if not recipe.get("description"):
            raise ValueError(f"Recipe {recipe_id} is missing description")

        if recipe_type == "composite":
            subtasks = recipe.get("subtasks", [])
            if not isinstance(subtasks, list) or not subtasks:
                raise ValueError(f"Composite recipe {recipe_id} must define non-empty subtasks")
            missing = [subtask for subtask in subtasks if subtask not in recipes]
            if missing:
                raise ValueError(f"Composite recipe {recipe_id} references missing subtasks: {missing}")

        if recipe_type == "primitive" and not recipe.get("skill_id") and not recipe.get("capability"):
            raise ValueError(f"Primitive recipe {recipe_id} must define skill_id or capability")


def get_recipe(recipe_id: str, recipes: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    return (recipes or load_recipes()).get(recipe_id)


def iter_recipes(recipes: Optional[Dict[str, Dict[str, Any]]] = None) -> Iterable[Dict[str, Any]]:
    return (recipes or load_recipes()).values()
