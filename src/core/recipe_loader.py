from pathlib import Path
import json

def load_recipes():
    base = Path(__file__).resolve().parents[2]
    path = base / "data" / "recipes.json"
    # print("Recipe path:", path)
    # print("Exists:", path.exists())
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return {item['recipe_id']: item for item in data}

# load_recipes()


