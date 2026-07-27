import unittest
import os
import json
from swe_agent.core.brain import OpenAIBrain
from swe_agent.core.memory import JSONExperienceStore
from pydantic import BaseModel, Field

# Mock tool schema để test binding
class MagicCalculatorSchema(BaseModel):
    number: int = Field(description="The number to double")

def magic_calculator(number: int) -> int:
    return number * 2

class TestMilestone2(unittest.TestCase):
    def setUp(self):
        self.test_json = "test_experience.json"
        self.memory = JSONExperienceStore(self.test_json)
        # Lưu ý: Cần set OPENAI_API_KEY trong môi trường hoặc mock ChatOpenAI
        self.brain = OpenAIBrain(model_name="gpt-4o", api_key="mock-key")

    def tearDown(self):
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def test_memory_storage(self):
        """Kiểm tra việc lưu trữ kinh nghiệm vào JSON."""
        task = "Fix syntax error"
        solution = "Add missing colon"
        self.memory.record_success(task, solution, {"accuracy": 1.0})
        
        experiences = self.memory.search_experience("Fix")
        self.assertEqual(len(experiences), 1)
        self.assertEqual(experiences[0]["task"], task)
        self.assertEqual(experiences[0]["solution"], solution)

    def test_brain_tool_binding(self):
        """Kiểm tra cơ chế bind tool của Brain."""
        tools = [magic_calculator]
        # Gọi hàm bind có mấu nối CASS
        bound_model = self.brain.bind_optimized_tools(tools)
        
        # Kiểm tra xem model đã được gắn tool chưa (LangChain nội bộ)
        self.assertTrue(hasattr(bound_model, "kwargs"))
        self.assertIn("tools", bound_model.kwargs)
        self.assertEqual(len(bound_model.kwargs["tools"]), 1)
        self.assertEqual(bound_model.kwargs["tools"][0]["function"]["name"], "magic_calculator")

if __name__ == "__main__":
    unittest.main()