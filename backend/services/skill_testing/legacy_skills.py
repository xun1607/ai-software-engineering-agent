from pydantic import BaseModel, Field
from swe_agent.skills.base import AgentSkill

class LegacySuggestFixInput(BaseModel):
    filename: str = Field(description="Filename to write")
    patched_code: str = Field(description="Content to write")

class LegacySuggestFixSkill(AgentSkill):
    name = "suggest_python_fix"
    description = "Write or overwrite python source code fix to sandbox."
    args_schema = LegacySuggestFixInput
    constraints = {"host": {"os": ["windows", "linux", "darwin"]}}

    def execute(self, sandbox, filename: str, patched_code: str):
        sandbox.write_file(filename, patched_code)
        return f"Successfully wrote fixed code to {filename}."

class LegacyReadContextInput(BaseModel):
    filename: str = Field(description="Filename to read")

class LegacyReadContextSkill(AgentSkill):
    name = "read_code_context"
    description = "Read code contents from workspace file."
    args_schema = LegacyReadContextInput
    constraints = {"host": {"os": ["windows", "linux", "darwin"]}}

    def execute(self, sandbox, filename: str):
        return sandbox.read_file(filename)
