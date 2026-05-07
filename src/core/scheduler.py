from langgraph.graph import END, START, StateGraph

from core.executor import executor_node
from core.planner import planner_node
from core.state import AgentState


def route_after_executor(state: AgentState):
    scheduler = state.get("scheduler", {})
    action = scheduler.get("next_action")
    if action == "replan":
        retry_count = scheduler.get("retry_count", 0)
        max_retries = scheduler.get("max_retries", 1)
        return "replan" if retry_count < max_retries else "end"
    if action == "continue":
        return "continue"
    return "end"


def replan_node(state: AgentState):
    scheduler = state.get("scheduler", {})
    return {
        "status": "replanning",
        "scheduler": {
            **scheduler,
            "retry_count": scheduler.get("retry_count", 0) + 1,
            "current_step": scheduler.get("current_step", 0),
            "next_action": "continue",
        },
    }


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("replanner", replan_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "continue": "executor",
            "replan": "replanner",
            "end": END,
        },
    )
    workflow.add_edge("replanner", "planner")

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    inputs = {"input": "Generate unit tests for a salary function"}

    for output in app.stream(inputs):
        for key in output:
            print(f"Node '{key}' completed.")
