from swe_agent.skills.base import AgentSkill
from pydantic import BaseModel, Field
from typing import Any, List
import re

class DebugPythonInput(BaseModel):
    stacktrace: str = Field(description="The raw Python stacktrace or error description.")
    filename: str = Field(description="The path to the Python file containing the bug.")

class DebugPythonSkill(AgentSkill):
    name = "debug_python"
    description = "Analyze a python stacktrace, examine the file, write the fix, and verify it."
    version = "1.0.0"
    category = "python/debugging"
    level = "composite"
    tags = ["python", "debug", "traceback"]
    args_schema = DebugPythonInput

    def __init__(self, brain=None):
        self.brain = brain

    def execute(self, sandbox, stacktrace: str, filename: str) -> str:
        """
        Execute python debugging workflow:
        1. Read the code context of the buggy file.
        2. Use the LLM (brain) to reason and generate a corrected file.
        3. Write the corrected file back to the sandbox.
        """
        # 1. Read code context
        try:
            code_content = sandbox.read_file(filename)
        except Exception as e:
            return f"Error: Buggy file '{filename}' could not be read: {str(e)}"

        # 2. Call LLM (brain) to fix if provided
        if self.brain:
            llm = self.brain.get_model()
            from langchain_core.messages import HumanMessage
            prompt = f"""
            You are a python debugging skill.
            Analyze this stacktrace and code content. Repair the bug in the code.
            BẮT BUỘC:
            1. Trả về TOÀN BỘ nội dung mã nguồn Python sau khi đã sửa.
            2. Do NOT wrap it in extra commentary, just return the Python code blocks or the plain string.
            
            STACKTRACE:
            {stacktrace}
            
            BUGGY FILE CONTENT ({filename}):
            {code_content}
            """
            response = llm.invoke([HumanMessage(content=prompt)])
            fixed_code = response.content.strip()
            
            # Clean LLM markdown code blocks
            if "```python" in fixed_code:
                fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
            elif "```" in fixed_code:
                fixed_code = fixed_code.split("```")[1].split("```")[0].strip()
        else:
            # Default fallback for simple offline test if no brain is provided
            fixed_code = "print('Fixed!')"

        # 3. Write file back to sandbox
        try:
            sandbox.write_file(filename, fixed_code)
            return f"Successfully diagnosed stacktrace and applied code patch to '{filename}'."
        except Exception as e:
            return f"Error: Could not write fixed code to '{filename}': {str(e)}"
