from core.scheduler import build_graph


app = build_graph()
inputs = {
    "input": "debug this java code: public class HelloWorld { public static void main(String[] args) { System.out.println('Hello, World!'); } }",
}

for output in app.stream(inputs):
    for key, value in output.items():
        print("\n" + "=" * 50)
        print(f"NODE: {key.upper()}")
        print("=" * 50)

        if key == "planner":
            plan = value["plan"]
            print(f"Strategy: {value.get('planning_strategy')}")
            print(f"Recipe  : {value.get('matched_recipe_id')}")
            print(f"Total Tasks: {len(plan)}")
            for idx, task in enumerate(plan, 1):
                print(f"{idx}. {task.get('skill_id')}")
                print(f"   -> {task.get('description')}")

        elif key == "executor":
            result = value["results"][0]
            print(f"Task   : {result['task_id']}")
            print(f"Skill  : {result['skill_id']}")
            print(f"Status : {'success' if result['success'] else 'failed'}")
            preview = str(result["output"])[:120].replace("\n", " ")
            print(f"Output : {preview}...")
