import yaml
from pydantic import create_model, BaseModel, Field
from typing import Dict, Any, List, Type
from swe_agent.skills.base import AgentSkill
from swe_agent.tools.base import BaseAgentTool

class MarkdownSkill(AgentSkill):
    """
    A generic skill that dynamically loads its schema and instructions 
    directly from a SKILL.md file and executes it using injected LLM and Tools.
    """
    def __init__(self, filepath: str, brain, tools: List[BaseAgentTool]):
        self.filepath = filepath
        self.brain = brain
        self.tools = tools  # Dependency Injection
        self._load_from_md()

    def _load_from_md(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        parts = content.split("---")
        if len(parts) < 3:
            raise ValueError(f"Invalid SKILL.md format in {self.filepath}")
            
        metadata = yaml.safe_load(parts[1])
        self.name = metadata.get("name")
        self.description = metadata.get("description", "")
        self.version = metadata.get("version", "1.0.0")
        self.category = metadata.get("category", "universal/generic")
        self.level = metadata.get("level", "atomic")
        self.tags = metadata.get("tags", [])
        self.constraints = metadata.get("constraints", {})
        self.instructions = parts[2].strip()
        
        # Dynamically build args_schema using Pydantic's create_model
        input_spec = metadata.get("input", {})
        properties = input_spec.get("properties", {})
        required = input_spec.get("required", [])
        
        fields = {}
        for prop_name, prop_val in properties.items():
            prop_type = str
            t_str = prop_val.get("type", "string")
            if t_str == "integer":
                prop_type = int
            elif t_str == "boolean":
                prop_type = bool
            elif t_str == "array":
                prop_type = list
                
            desc = prop_val.get("description", "")
            if prop_name in required:
                fields[prop_name] = (prop_type, Field(description=desc))
            else:
                fields[prop_name] = (prop_type, Field(default=None, description=desc))
                
        # Generate Pydantic class dynamically at runtime
        self.args_schema = create_model(
            f"{self.name.replace('-', '_')}_args",
            **fields
        )

    def execute(self, sandbox, **kwargs) -> Any:
        """
        Dynamically execute the skill instructions inside the sandbox.
        """
        if not self.brain:
            raise ValueError("Error: Brain dependency must be provided to execute MarkdownSkill.")

        # Bind the injected tools using the BaseAgentTool abstraction
        llm = self.brain.get_model().bind_tools(self.tools)
        
        prompt = f"""
        You are executing the Agent Skill: {self.name}
        Description: {self.description}
        
        Instructions to follow:
        {self.instructions}
        
        Inputs:
        {kwargs}
        
        Use the provided tools in the sandbox to complete the task.
        Return the final output as a clean JSON matching the expected output format.
        """
        
        from langchain_core.messages import HumanMessage, ToolMessage
        messages = [HumanMessage(content=prompt)]
        
        # Run local tool loop for LLM reasoning & action
        for _ in range(5):
            response = llm.invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                break
                
            for tool_call in response.tool_calls:
                # Find corresponding tool from injected list
                tool = next((t for t in self.tools if t.name == tool_call["name"]), None)
                if tool:
                    result = tool.execute(sandbox, **tool_call["args"])
                    messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(result)))
                else:
                    messages.append(ToolMessage(tool_call_id=tool_call["id"], content="Error: Tool not found"))
                    
        final_text = messages[-1].content
        try:
            import json
            if "```json" in final_text:
                final_text = final_text.split("```json")[1].split("```")[0].strip()
            elif "```" in final_text:
                final_text = final_text.split("```")[1].split("```")[0].strip()
            return json.loads(final_text)
        except Exception:
            return {"result": final_text}
