from core.scheduler import build_graph


app = build_graph()
# inputs = {
#     "input": (
#         "Generate unit tests for this code:\n"
#         "```python\n"
#         "def calculate_salary(hours, rate):\n"
#         "    if hours < 0 or rate < 0:\n"
#         "        raise ValueError('hours and rate must be positive')\n"
#         "    return hours * rate\n"
#         "```"
#     ),
# }

inputs = {
    "input": "Hệ thống đang gặp lỗi NullPointerException ở dòng 45, hãy xử lý giúp tôi."
}
for output in app.stream(inputs):
    for key, value in output.items():
        print("\n" + "=" * 50)
        print(f"NODE: {key.upper()}")
        print("=" * 50)

        if key == "planner":
            plan = value["plan"]
            tasks = plan.get("tasks", [])
            print(f"Strategy: {value.get('planning_strategy')}")
            print(f"Recipe  : {value.get('matched_recipe_id')}")
            print(f"Total Tasks: {len(tasks)}")
            for idx, task in enumerate(tasks, 1):
                deps = ", ".join(task.get("depends_on", [])) or "none"
                print(f"{idx}. {task.get('skill_id')} deps=[{deps}]")
                print(f"   -> {task.get('description')}")

        elif key == "executor":
            result = value["results"][-1]
            memory = value.get("context_memory", {})
            print(f"Task   : {result['task_id']}")
            print(f"Skill  : {result['skill_id']}")
            print(f"Status : {'success' if result['success'] else 'failed'}")
            print(f"Memory : {list(memory.get('task_results', {}).keys())}")
            preview = str(result["output"])[:160].replace("\n", " ")
            print(f"Output : {preview}...")
