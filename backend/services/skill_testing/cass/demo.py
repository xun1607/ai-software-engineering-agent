import os
from typing import Annotated, Any, List, Union
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from cass.core import CASS
from cass.adapter.langchain_adapter import LangChainCASSAdapter

# --- 1. SETUP CASS & TOOLS ---
cass_system = CASS("agent_learning.db")

@tool
def power_calculator(base: int, exp: int):
    """Calculates power of a number. Highly reliable."""
    return base ** exp

@tool
def legacy_calculator(base: int, exp: int):
    """Old calculator. Often fails on large numbers."""
    import random
    if random.random() < 0.8: # 80% tỉ lệ lỗi
        raise Exception("Legacy System Hardware Failure")
    return base ** exp

raw_tools = [power_calculator, legacy_calculator]
# Biến các tool này thành Profile để CASS hiểu
tool_profiles = [LangChainCASSAdapter.to_cass_profile(t) for t in raw_tools]

# --- 2. ĐỊNH NGHĨA TRẠNG THÁI (STATE) ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    selected_tools: List[Any] # Danh sách tool CASS đã lọc

# --- 3. CÁC NÚT XỬ LÝ (NODES) ---

def cass_filter_node(state: AgentState):
    """Nút CASS: Lọc tool trước khi đưa cho LLM."""
    last_message = state['messages'][-1].content
    session_id = "demo-session-001"
    
    # CASS thực hiện phép thuật của mình
    optimized_profiles = cass_system.get_optimized_skills(
        tool_profiles, session_id, subtask=last_message, top_k=1
    )
    
    # Lấy ra tool thật tương ứng
    selected_names = [p['name'] for p in optimized_profiles]
    active_tools = [t for t in raw_tools if t.name in selected_names]
    
    print(f"--- CASS SELECTED: {selected_names} ---")
    return {"selected_tools": active_tools}

def call_model_node(state: AgentState):
    """Nút LLM: Nhận diện tool đã được lọc và ra quyết định."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    # Bind các tool đã được CASS lọc vào LLM
    llm_with_tools = llm.bind_tools(state['selected_tools'])
    response = llm_with_tools.invoke(state['messages'])
    return {"messages": [response]}

def execute_tool_node(state: AgentState):
    """Nút thực thi: Chạy Tool qua Proxy để ghi telemetry."""
    last_message = state['messages'][-1]
    results = []
    
    for tool_call in last_message.tool_calls:
        # Tìm tool gốc
        tool_obj = next(t for t in raw_tools if t.name == tool_call['name'])
        # Bọc qua Proxy của CASS
        proxied_tool = cass_system.wrap_skill(tool_obj, "demo-session-001")
        
        try:
            output = proxied_tool.invoke(tool_call['args'])
            results.append(ToolMessage(tool_call_id=tool_call['id'], content=str(output)))
        except Exception as e:
            results.append(ToolMessage(tool_call_id=tool_call['id'], content=f"Error: {str(e)}"))
            
    return {"messages": results}

# --- 4. XÂY DỰNG ĐỒ THỊ (GRAPH) ---
workflow = StateGraph(AgentState)

workflow.add_node("cass_filter", cass_filter_node)
workflow.add_node("llm", call_model_node)
workflow.add_node("tools", execute_tool_node)

workflow.set_entry_point("cass_filter")
workflow.add_edge("cass_filter", "llm")
workflow.add_edge("llm", "tools")
workflow.add_edge("tools", "llm") # Quay lại LLM để trả kết quả cuối cùng

app = workflow.compile()

# --- 5. CHẠY THỰC NGHIỆM ---
input_msg = HumanMessage(content="Calculate 2 to the power of 10")

print("\n--- LẦN CHẠY 1 ---")
app.invoke({"messages": [input_msg]})

print("\n--- LẦN CHẠY 2 ---")
app.invoke({"messages": [input_msg]})