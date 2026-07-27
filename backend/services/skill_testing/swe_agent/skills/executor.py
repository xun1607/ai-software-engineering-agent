from typing import Any, Dict, Optional
from .registry import SkillRegistry

class SkillExecutor:
    """
    Orchestrates Skill execution and handles performance logging via CASS.
    Runs skills inside the sandbox runtime and captures execution telemetry.
    """
    def __init__(self, 
                registry: SkillRegistry, 
                sandbox: Any, 
                cass_bridge: Optional[Any] = None):
        self.registry = registry
        self.sandbox = sandbox
        self.cass_bridge = cass_bridge

    def run(self, tool_call: Dict[str, Any], session_id: str) -> str:
        """
        Execute a skill requested by the LLM.
        """
        skill_name = tool_call['name']
        args = tool_call['args']
        
        skill = self.registry.get_skill(skill_name)
        if not skill:
            return f"Error: Skill '{skill_name}' is not registered in the system."

        execute_fn = skill.execute
        if self.cass_bridge:
            execute_fn = self.cass_bridge.wrap_skill_execution(
                skill_fn=skill.execute, 
                session_id=session_id
            )

        try:
            result = execute_fn(sandbox=self.sandbox, **args)
            return str(result)
        except Exception as e:
            return f"Execution Error in Skill '{skill_name}': {str(e)}"