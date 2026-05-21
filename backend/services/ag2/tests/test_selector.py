import pytest
from unittest.mock import MagicMock
from skill_selector_module.selector import ContextBasedSkillSelector
from skill_selector_module.schemas import SkillSelectionResult

def test_selector_with_real_registry_api():
    mock_openai = MagicMock()
    mock_selection_result = SkillSelectionResult(
        selected_skill_id="any-id",
        skill_name="test-skill",
        reasoning="Logic test",
        extracted_arguments={"param": "value"}
    )
    mock_completion = MagicMock()
    mock_completion.choices[0].message.parsed = mock_selection_result
    mock_openai.beta.chat.completions.parse.return_value = mock_completion

    # KHỞI TẠO SELECTOR VỚI URL THẬT (sau khi đã chạy Docker)
    REAL_REGISTRY_URL = "http://localhost:8001" 
    selector = ContextBasedSkillSelector(client=mock_openai, skill_registry_url=REAL_REGISTRY_URL)

    # CHẠY THỬ
    # Bước này sẽ gọi hàm _fetch_skills_from_registry() thật qua httpx
    try:
        result = selector.select_best_skill(
            current_task_description="Cần tìm lỗi trong code Python",
            accumulated_context={"source_code": "print('hello')"}
        )
        
        print(f"\n✅ Kết nối API thành công!")
        print(f"✅ Skill ID chọn được: {result.selected_skill_id}")
        
    except Exception as e:
        pytest.fail(f"❌ Lỗi khi gọi API thật từ Docker: {e}")

if __name__ == "__main__":
    test_selector_with_real_registry_api()