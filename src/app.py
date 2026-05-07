from core.scheduler import build_graph


app = build_graph()
inputs = {
    "input": "Hãy viết unit test cho hàm tính lương"
}
for output in app.stream(inputs):
    for key, value in output.items():

        print("\n" + "="*50)
        print(f"NODE: {key.upper()}")
        print("="*50)

        # ===== PLANNER =====
        if key == "planner":

            plan = value["plan"]

            print(f"Total Tasks: {len(plan)}")

            for idx, task in enumerate(plan, 1):
                print(f"{idx}. {task['skill_id']}")
                print(f"   -> {task['description']}")

        # ===== EXECUTOR =====
        elif key == "executor":

            result = value["results"][0]

            print(f"Task   : {result['task_id']}")
            print(f"Skill  : {result['skill']}")

            preview = result["output"][:120].replace("\n", " ")

            print(f"Output : {preview}...")