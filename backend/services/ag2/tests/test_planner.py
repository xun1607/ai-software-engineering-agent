import pytest
from unittest.mock import MagicMock
from planner_module.planner import PlannerModule
from planner_module.schemas import TaskStep, ExecutionPlan
####### TEST DESCRIPTION ########
# Mục tiêu: Kiểm tra logic lập kế hoạch của PlannerModule.generate_plan()
# Mock OpenAI client để giả lập phản hồi có cấu trúc từ LLM, sau đó kiểm tra xem Planner có trích xuất đúng thông tin và trả về kế hoạch đúng định dạng không
# User Request
#    ↓
# PlannerModule.generate_plan()
#    ↓
# OpenAI Structured Output API
#    ↓
# ExecutionPlan
#    ↓
# TaskStep[]


def test_generate_plan_logic():
    # Setup Mock
    mock_client = MagicMock()
    planner = PlannerModule(client=mock_client)
    mock_parsed_response = ExecutionPlan(steps=[
        TaskStep(step_id=1, thought="Cần lấy dữ liệu", task_description="Đọc file main.py và tìm lỗi sai", status="PENDING")
    ])
    # Mock hàm .parse().choices[0].message.parsed
    mock_completion = MagicMock()
    mock_completion.choices[0].message.parsed = mock_parsed_response
    mock_client.beta.chat.completions.parse.return_value = mock_completion

    # Thực thi
    plan = planner.generate_plan("Lấy dữ liệu từ file main.py", "No history")

    # Kiểm tra (Assert)
    assert len(plan.steps) == 1
    assert plan.steps[0].step_id == 1
    assert "main.py" in plan.steps[0].task_description
    # Đảm bảo hàm parse được gọi đúng model
    mock_client.beta.chat.completions.parse.assert_called_once()