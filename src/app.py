from core.scheduler import build_graph


def _safe(text):
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


app = build_graph()
inputs = {
    "input": "viết test kiểm thử unit test",
}

final_state = app.invoke(inputs)

plan = final_state.get("plan", {})
metrics = final_state.get("metrics", {})
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
print(f"Strategy      : {final_state.get('planning_strategy')}")
print(f"Recipe        : {final_state.get('matched_recipe_id')}")
print(f"Status        : {final_state.get('status')}")
print(f"Total Tasks   : {len(plan.get('tasks', []))}")
print(f"Total Runs    : {len(final_state.get('results', []))}")
print(f"Total Retries : {metrics.get('total_retries', 0)}")
print(f"Replanned     : {final_state.get('is_replanned', False)}")
print(f"Total Tokens  : {metrics.get('total_tokens', 0)}")
print(f"Final Cost    : ${metrics.get('estimated_cost', 0.0):.6f}")

last_output = final_state.get("context_memory", {}).get("last_output")
print(f"Last Output   : {_safe(str(last_output)[:160])}...")
