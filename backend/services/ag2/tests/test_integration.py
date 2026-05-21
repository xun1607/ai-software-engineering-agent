import os
from openai import OpenAI
from planner_module.planner import PlannerModule
from skill_selector_module.selector import ContextBasedSkillSelector
from executor_module.executor import LLMSkillExecutor
from orchestrator_module.mock import MockOrchestratorGraph

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG ---
OS_API_KEY = os.getenv("OPENAI_API_KEY")
REGISTRY_URL = "http://localhost:8001" 

def main():
    client = OpenAI(api_key=OS_API_KEY)

    planner = PlannerModule(client=client)
    selector = ContextBasedSkillSelector(client=client, skill_registry_url=REGISTRY_URL)
    executor = LLMSkillExecutor(client=client)

    orchestrator = MockOrchestratorGraph(
        planner_module=planner, 
        skill_selector=selector,
        executor_module=executor
    )
    
    app = orchestrator.compile()

    #  Kịch bản Test thực tế
    # muốn Agent sửa một lỗi Python cụ thể
    initial_state = {
        "user_goal": "Tôi có đoạn code: 'print(x + y)'. Hãy dùng kỹ năng phù hợp để sửa nó, biết x=5 và y là None.",
        "chat_history": "",
        "execution_plan": [],
        "current_step_index": 0,
        "accumulated_context": {
            "error_type": "TypeError",
            "file_name": "debug_me.py"
        },
        "latest_error_feedback": None,
        "current_retry_count": 0,
        "extracted_arguments": {}
    }

    print("🔥 --- AGENT CHÍNH THỨC --- 🔥")
    for output in app.stream(initial_state):
        for node_name, state_update in output.items():
            print(f"\n✅ Hoàn thành Node: [{node_name.upper()}]")
            # Log đặc biệt cho Executor để xem LLM xử lý skill thế nào
            if node_name == "execute_skill_node":
                print(f"📥 KẾT QUẢ THỰC THI THẬT:")
                print(state_update.get("latest_step_output", {}).get("result"))

    print("\n🏁 --- TẤT CẢ CÁC BƯỚC ĐÃ XỬ LÝ XONG ---")

if __name__ == "__main__":
    main()