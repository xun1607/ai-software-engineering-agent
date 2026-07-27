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
        
        logs_to_append = []
        for tool_call in last_message.tool_calls:
            result = self.executor.run(tool_call, session_id)
            res_str = str(result)
            
            # Log execution details for virtual terminal
            tool_name = tool_call.get('name', 'unknown')
            tool_args = tool_call.get('args', {})
            logs_to_append.append({
                "tool": tool_name,
                "args": tool_args,
                "output": res_str[:3000]  # Store clean output snippet for terminal display
            })
            
            if len(res_str) > 2000:
                res_str = res_str[:1000] + "\n\n... [OUTPUT TRUNCATED BY CASS AGENT TO PREVENT TOKEN BLOAT] ...\n\n" + res_str[-1000:]
            outputs.append(ToolMessage(tool_call_id=tool_call['id'], content=res_str))
            
            # Extract target filename for the validation node
            target_fn = tool_args.get('filename') or tool_args.get('filepath') or tool_args.get('path') or tool_args.get('file')
            if target_fn:
                current_file = target_fn
            
        res = {"messages": outputs}
        if current_file:
            res["current_file"] = current_file
            
        if logs_to_append:
            res["execution_logs"] = logs_to_append
            
        return res