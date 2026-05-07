from langgraph.graph import END, START, StateGraph

from core.evaluator import evaluator_node, route_after_evaluator
from core.executor import executor_node
from core.planner import planner_node
from core.state import AgentState


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("evaluator", evaluator_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "evaluator")
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "retry": "executor",
            "continue": "executor",
            "replan": "planner",
            "end": END,
        },
    )

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    inputs = {"input": "viet test kiem thu unit test"}

    for output in app.stream(inputs):
        for key in output:
            print(f"Node '{key}' completed.")
