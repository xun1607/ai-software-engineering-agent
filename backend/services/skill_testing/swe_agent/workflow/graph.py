from langgraph.graph import StateGraph, END
from .nodes.reasoning import ReasoningNode
from .nodes.action import ActionNode
from .nodes.verify import VerifyNode
from .router import edge_router
from .state import AgentState

def create_swe_agent(brain, sandbox, skills, cass_bridge=None):
    """
    Construct and compile the LangGraph workflow representing the Agent loop.
    Connects the ReasoningNode, ActionNode, and VerifyNode with conditional routing.
    """
    reasoning = ReasoningNode(brain, skills, cass_bridge)
    action = ActionNode(sandbox, skills, cass_bridge)
    verify = VerifyNode(sandbox)

    builder = StateGraph(AgentState)
    
    builder.add_node("think", reasoning)
    builder.add_node("act", action)
    builder.add_node("check", verify)

    builder.set_entry_point("think")
    
    builder.add_edge("think", "act")
    builder.add_edge("act", "check")
    
    builder.add_conditional_edges(
        "check",
        edge_router,
        {
            "end": END,
            "retry": "think"
        }
    )

    return builder.compile()