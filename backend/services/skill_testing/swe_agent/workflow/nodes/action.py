from langchain_core.messages import ToolMessage
from swe_agent.skills.executor import SkillExecutor
from swe_agent.skills.registry import SkillRegistry

class ActionNode:
    """
    LangGraph node responsible for executing the skill actions called by the LLM.
    Registers candidate skills and executes them inside the sandbox using SkillExecutor.
    """
    def __init__(self, sandbox, skills, cass_bridge=None):
        # Register skills into a temporary local registry for execution
        registry = SkillRegistry()
        for s in skills:
            registry.register(s)
            
        self.executor = SkillExecutor(registry, sandbox, cass_bridge)

    def __call__(self, state):
        """
        Execute all skill calls emitted by the LLM in the last message.
        """
        last_message = state['messages'][-1]
        session_id = state.get("session_id", "default_session")
        outputs = []
        current_file = None
        
        for tool_call in last_message.tool_calls:
            # Execute the skill inside the sandbox
            result = self.executor.run(tool_call, session_id)
            outputs.append(ToolMessage(tool_call_id=tool_call['id'], content=str(result)))
            
            # Extract target filename for the validation node (e.g. write_file)
            if tool_call.get('name') == 'write_file' and 'filename' in tool_call.get('args', {}):
                current_file = tool_call['args']['filename']
            
        res = {"messages": outputs}
        if current_file:
            res["current_file"] = current_file
        return res