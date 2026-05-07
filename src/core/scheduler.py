# langgraph state machine
from typing import Annotated, List, TypedDict
import operator
from langgraph.graph import StateGraph, START, END

from core.planner import planner_node
from core.executor import executor_node

class AgentState(TypedDict):
    task_input: str
    context: dict   
    plan: List[dict]       # Danh sách subtasks từ HTN
    history: Annotated[List[str], operator.add] # Lịch sử thực thi để tiêp tục cải thiện kế hoạch
    artifacts: dict        # Kết quả đầu ra
    
    


# ===== STATE =====
class AgentState(TypedDict):
    input: str
    plan: List[dict]
    results: Annotated[List[str], operator.add]
    current_step: int


# ===== CONTROL FLOW =====
def should_continue(state: AgentState):
    if state["current_step"] < len(state["plan"]):
        return "continue"
    return "end"


# ===== BUILD GRAPH =====
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
            "end": END
        }
    )

    return workflow.compile()


# ===== RUN (optional) =====
if __name__ == "__main__":
    app = build_graph()

    inputs = {
        "input": "Hãy viết unit test cho hàm tính lương"
    }

    for output in app.stream(inputs):
        for key in output:
            print(f"Node '{key}' đã hoàn thành.")