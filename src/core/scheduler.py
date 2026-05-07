from langgraph.graph import END, START, StateGraph

from core.executor import executor_node
from core.planner import planner_node
from core.state import AgentState


def should_continue(state: AgentState):
    if state.get("status") == "failed":
        return "end"
    if state.get("current_step", 0) < len(state.get("plan", [])):
        return "continue"
    return "end"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "continue": "executor",
            "end": END,
        },
    )

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    inputs = {"input": "Hay viet unit test cho ham tinh luong"}

    for output in app.stream(inputs):
        for key in output:
            print(f"Node '{key}' completed.")