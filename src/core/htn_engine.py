from typing import List

# ===== STATE =====
# class AgentState(TypedDict):
#     input: str
#     plan: List[dict]   # ⚠️ sửa lại đúng type
#     results: Annotated[List[str], operator.add]
#     current_step: int

# ===== HTN LOGIC =====


def htn_recursive_decompose(recipe_id: str, lookup_table: dict) -> List[dict]:
    """
    Hàm đệ quy phân rã task HTN
    Composite -> Primitive
    """
    recipe = lookup_table.get(recipe_id)

    if not recipe:
        return []

    if recipe["type"] == "primitive":
        return [{
            "id": recipe_id,
            "skill_id": recipe.get("skill_id"),
            "description": recipe.get("description")
        }]

    primitive_tasks = []

    for sub_id in recipe.get("subtasks", []):
        primitive_tasks.extend(
            htn_recursive_decompose(sub_id, lookup_table)
        )

    return primitive_tasks

# ===== PLANNER =====
# def planner_node(state: AgentState):
    recipes = load_recipes()

    # TODO: sau này thay bằng router
    target_recipe = "unit_test_gen"

    plan = htn_recursive_decompose(target_recipe, recipes)

    print(f"[Planner] Đã phân rã '{target_recipe}' thành {len(plan)} bước.")

    return {
        "plan": plan,
        "current_step": 0
    }


# ===== EXECUTOR =====
# def executor_node(state: AgentState):
    step_idx = state["current_step"]
    task = state["plan"][step_idx]

    print(f"[Executor] Chạy: {task['skill_id']}")

    result = run_task(task, state["input"])

    return {
        "results": [f"[{task['id']}] {result[:50]}..."],
        "current_step": step_idx + 1
    }


# ===== CONTROL FLOW =====
# def should_continue(state: AgentState):
    if state["current_step"] < len(state["plan"]):
        return "continue"
    return "end"


# ===== BUILD GRAPH =====
# workflow = StateGraph(AgentState)

# workflow.add_node("planner", planner_node)
# workflow.add_node("executor", executor_node)

# workflow.add_edge(START, "planner")
# workflow.add_edge("planner", "executor")

# workflow.add_conditional_edges(
#     "executor",
#     should_continue,
#     {
#         "continue": "executor",
#         "end": END
#     }
# )

# app = workflow.compile()
# build_graph()


