import unittest
import os
import shutil
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

# Import system components
from swe_agent.core.brain import OpenAIBrain
from swe_agent.core.sandbox import LocalSandbox
from swe_agent.workflow.graph import create_swe_agent
from swe_agent.skills.base import AgentSkill

# --- MOCK SKILL FOR TESTING ---
class WriteFileInput(BaseModel):
    filename: str = Field(description="Tên file cần ghi")
    content: str = Field(description="Nội dung mã nguồn Python")

class WriteFileSkill(AgentSkill):
    name = "write_file"
    description = "Ghi nội dung vào một file trong sandbox."
    args_schema = WriteFileInput

    def execute(self, sandbox, filename: str, content: str):
        sandbox.write_file(filename, content)
        return f"Đã ghi file {filename} thành công."

# --- UNIT TEST CLASS ---
class TestMilestone4Graph(unittest.TestCase):
    def setUp(self):
        self.workspace = "./test_m4_workspace"
        self.sandbox = LocalSandbox(self.workspace)
        # Use GPT-4o for robust reasoning capabilities during testing
        self.brain = OpenAIBrain(model_name="gpt-4o")
        self.skills = [WriteFileSkill()]
        self.agent = create_swe_agent(self.brain, self.sandbox, self.skills)

    def tearDown(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    def test_agent_self_healing_flow(self):
        """
        Scenario: Ask the Agent to write a Python script with syntax error.
        Objective: The graph should run the 'check' node, catch the SyntaxError,
                   and route back to the 'think' node to self-heal.
        """
        print("\n🚀 Starting Self-healing Test...")
        
        task = (
            "Hãy tạo file 'buggy.py' in ra chuỗi 'Fixed!'. "
            "BẮT BUỘC: Ở lần đầu tiên, hãy viết thiếu dấu ngoặc đóng ')' để tôi test tính năng sửa lỗi của hệ thống."
        )
        
        initial_state = {
            "messages": [HumanMessage(content=task)],
            "iteration_count": 0,
            "is_valid": False,
            "feedback": None
        }

        # Execute the Graph with a reasonable recursion limit
        final_state = self.agent.invoke(initial_state, {"recursion_limit": 15})

        # --- VERIFICATION ---
        
        # 1. Iteration count must be > 1 as it should fail once
        self.assertGreater(final_state["iteration_count"], 1)
        print(f"✅ Agent healed itself in {final_state['iteration_count']} iterations.")

        # 2. Final state must be valid
        self.assertTrue(final_state["is_valid"])

        # 3. Read the actual written file in the sandbox
        actual_content = self.sandbox.read_file("buggy.py")
        print(f"✅ Final Code in Sandbox: {actual_content.strip()}")
        
        # Final code should have closing bracket
        self.assertIn(")", actual_content)
        self.assertIn("Fixed!", actual_content)

if __name__ == "__main__":
    unittest.main()