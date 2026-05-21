import pytest
from unittest.mock import MagicMock
from planner_module.planner import PlannerModule, ExecutionPlan
from planner_module.schemas import TaskStep
from orchestrator_module.mock import MockOrchestratorGraph # Thay bằng tên file của bạn

def test_orchestrator_full_flow():
    mock_planner = MagicMock()
    mock_selector = MagicMock()
    
    # Giả lập Planner trả về 1 bước
    mock_planner.generate_plan.return_value = ExecutionPlan(steps=[
        TaskStep(step_id=1, thought="Test", task_description="Sửa lỗi file main.py", status="PENDING")
    ])
    
    # Giả lập Selector trả về 1 ID
    mock_selector.select_best_skill.return_value = "email_skill_01"

    # 2. Khởi tạo Graph
    orchestrator = MockOrchestratorGraph(mock_planner, mock_selector)
    app = orchestrator.compile()

    # 3. Chạy thử với Input đầu vào
    inputs = {
        "user_goal": "Hãy sửa lỗi file main.py",
        "chat_history": "",
        "accumulated_context": {},
        "current_step_index": 0
    }
    
    final_state = app.invoke(inputs)

    # 4. Assert (Kiểm chứng)
    assert "final_response" in final_state
    assert final_state["current_step_index"] == 1 # Đã tăng sau khi chạy 1 bước
    assert "email_skill_01" in final_state["final_response"]
    print("\n✅ Test Orchestrator thành công!")

if __name__ == "__main__":
    test_orchestrator_full_flow()