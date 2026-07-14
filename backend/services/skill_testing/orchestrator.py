import asyncio
import json
from typing import List, Dict, Any

from langgraph.graph import StateGraph, END

from services.skill_testing.core.llm_client import OpenAIClient
from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.core.skill_client import SkillExecutionClient

from services.skill_testing.core.plan_node import plan_node
from services.skill_testing.core.select_skill_node import select_skill_node
from services.skill_testing.core.execute_node import execute_node
from services.skill_testing.core.evaluate_node import evaluate_node

import os
import httpx
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("[WARNING] OPENAI_API_KEY environment variable is not set.")
    api_key = "mock_key"

def route_decision(state: AgentState):
    if state.is_finished:
        print(f"\n🏁 [SYSTEM END] -> Vòng lặp khép kín kết thúc!")
        print(f"📄 Kết quả cuối cùng: {state.final_answer}")
        print(f"📊 Chỉ số thực thi: Total Steps attempted: {state.step_count}")
        return END
        
    if state.step_count >= state.max_total_steps:
        print(f"\n🚨 [CIRCUIT BREAKER] Cảnh báo lặp vô hạn! Ngắt luồng tại bước thứ {state.step_count}")
        return END

    if state.current_step_idx < len(state.plan):
        if state.retry_count > 0:
            print(f"🔄 [AG2 ROUTER] Phát hiện lỗi thực thi. Kích hoạt Retry vòng {state.retry_count} trên tác vụ hiện tại.")
            return "executor_node"
            
        print(f"➡️ [AG2 ROUTER] Ngữ cảnh hợp lệ. Di chuyển tới tác vụ tiếp theo trong kế hoạch: '{state.plan[state.current_step_idx]}'")
        return "select_skill_node"
        
    if not state.plan or state.current_step_idx >= len(state.plan):
        print(f"🔄 [AG2 ROUTER] Plan trống hoặc cần Replan. Điều hướng quay về Node Planner.")
        return "plan_node"

    print(f"➡️ [AG2 ROUTER] Task hiện tại hoàn tất. Di chuyển tới bước tiếp theo trong plan.")
    return "select_skill_node"

    return END


def get_compiled_workflow(llm_client, skill_client):
    async def p_node(state):
        return await plan_node(state, llm_client)

    async def s_node(state):
        return await select_skill_node(state)

    async def ex_node(state):
        return await execute_node(state, llm_client, skill_client)

    async def ev_node(state):
        return await evaluate_node(state, llm_client, skill_client)

    workflow = StateGraph(AgentState)
    
    workflow.add_node("plan_node", p_node)
    workflow.add_node("select_skill_node", s_node)
    workflow.add_node("executor_node", ex_node)
    workflow.add_node("evaluate_node", ev_node)


    workflow.set_entry_point("plan_node")
    workflow.add_edge("plan_node", "select_skill_node")
    workflow.add_edge("select_skill_node", "executor_node")
    workflow.add_edge("executor_node", "evaluate_node")
    

    workflow.add_conditional_edges("evaluate_node", route_decision)

    return workflow.compile()

async def run_pipeline(
    code_content: str,              
    filename: str,                  
    stacktrace: str,                
    message: str,      
    workspace_path: str = None,    
    baseline_mode: str = "B4",
    skill_client = None
):
    print("=========================================================")
    print("🚀 KÍCH HOẠT ĐỒ THỊ ĐIỀU PHỐI AG2 ──> KẾT NỐI AG1 🚀")
    print("=========================================================\n")

    print(f"api key:  {api_key}\n")
    
    #  Nhận dữ liệu đệm get_cached_skills() từ tệp server.py để tối ưu hóa
    try:
        from services.skill_testing.server import get_cached_skills
        tool_list = await get_cached_skills()
        print(f"✅ Tải thành công {len(tool_list)} kỹ năng từ Cache (server.py)!")
    except Exception as e:
        print(f"❌ Không thể gọi get_cached_skills từ server.py ({str(e)}). Dùng dữ liệu dự phòng.")
        tool_list = [
            {"name": "analyze-stacktrace", "description": "Phân tích java stacktrace", "skill_id": "analyze-stacktrace"},
            {"name": "read-code-context", "description": "Đọc mã nguồn Java xung quanh dòng chỉ định", "skill_id": "read-code-context"},
            {"name": "suggest-java-fix", "description": "Ghi đè bản vá lỗi Java", "skill_id": "suggest-java-fix"},
            {"name": "debug-java-null-pointer", "description": "Biên dịch javac kiểm tra lỗi cú pháp Java", "skill_id": "debug-java-null-pointer"}
        ]

    #  Chỉ build index một lần duy nhất nếu chưa lập ma trận Vector Embedding
    if semantic_registry._embeddings is None:
        semantic_registry.build_index(tool_list)
    else:
        print("⚡ [REGISTRY] Bỏ qua xây dựng index vector vì Registry đã được lập chỉ mục trước đó.")

    if skill_client is None:
        skill_client = SkillExecutionClient(workspace_path=workspace_path)
    llm_client = OpenAIClient(api_key=api_key)
    
    if code_content is None:
        code_content = """ """
        
    skill_client.setup_initial_workspace(code_content, filename)
    
    initial_state = {
        "user_context": {
            "code": code_content,
            "filename": filename,
            "stacktrace": stacktrace,
            "message": message,
            "baseline_mode": baseline_mode
        },
        "plan": [],
        "current_step_idx": 0,
        "step_count": 0,
        "history": []
    }
    
    app = get_compiled_workflow(llm_client, skill_client)
    try:
        graph_image_bytes = app.get_graph().draw_mermaid_png()
        with open("langgraph_workflow.png", "wb") as f:
            f.write(graph_image_bytes)
        print("🎨 [ILLUSTRATE] Đã xuất sơ đồ đồ thị trạng thái thành công: 'langgraph_workflow.png'")
    except Exception as e:
        print(f"⚠️ Không thể xuất ảnh đồ thị trực tiếp: {e}. Bạn có thể dùng mã Mermaid thay thế.")
    final_output = await app.ainvoke(initial_state)
    print("\n🏁 [SYSTEM END] Luồng chạy tích hợp thực tế hoàn thành rực rỡ!")
    return final_output
