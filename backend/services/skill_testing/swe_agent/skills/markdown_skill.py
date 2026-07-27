import yaml
from pydantic import create_model, BaseModel, Field
from typing import Dict, Any, List, Type
from swe_agent.skills.base import AgentSkill
from swe_agent.tools.base import BaseAgentTool

class DynamicMarkdownSkill(AgentSkill):
    """
    A generic skill that dynamically loads schema and instructions 
    directly from a SKILL.md file and executes it using an LLM (ReasoningAgent) and Tools.
    """
    def __init__(self, filepath: str, brain, tools: List[BaseAgentTool]):
        self.filepath = filepath
        self.brain = brain
        self.tools = tools  # Dependency Injection
        self._load_from_md()

    def _load_from_md(self):
        import os
        with open(self.filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        parts = content.split("---")
        if len(parts) >= 3:
            raw_yaml = parts[1].strip()
            instructions_text = "---".join(parts[2:]).strip()
        elif len(parts) == 2:
            raw_yaml = parts[0].strip()
            instructions_text = parts[1].strip()
        else:
            raw_yaml = ""
            instructions_text = content.strip()
            
        metadata = {}
        if raw_yaml:
            try:
                parsed = yaml.safe_load(raw_yaml)
                if isinstance(parsed, dict):
                    metadata = parsed
            except Exception:
                # Fallback line-by-line key-value parser if PyYAML encounters non-standard syntax
                metadata = {}
                for line in raw_yaml.splitlines():
                    line_s = line.strip()
                    if ":" in line_s and not line_s.startswith("#"):
                        k, v = line_s.split(":", 1)
                        k_clean = k.strip().strip("'\"").strip(",")
                        v_clean = v.strip().strip("'\"")
                        if k_clean and k_clean not in metadata:
                            metadata[k_clean] = v_clean
                            
        if not isinstance(metadata, dict):
            metadata = {}
            
        default_name = os.path.basename(os.path.dirname(self.filepath)).replace("_", "-")
        self.name = metadata.get("name") or default_name
        self.name = str(self.name).replace(" ", "-").replace("/", "-")
        self.description = str(metadata.get("description") or f"Dynamic skill loaded from {self.name}.")
        self.version = str(metadata.get("version", "1.0.0"))
        self.category = str(metadata.get("category", "universal/generic"))
        self.level = str(metadata.get("level", "atomic"))
        
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        self.tags = tags if isinstance(tags, list) else []
        
        constraints = metadata.get("constraints", {})
        self.constraints = constraints if isinstance(constraints, dict) else {}
        self.instructions = instructions_text
        
        # Dynamically build args_schema using Pydantic's create_model
        input_spec = metadata.get("input", {})
        properties = input_spec.get("properties", {}) if isinstance(input_spec, dict) else {}
        required = input_spec.get("required", []) if isinstance(input_spec, dict) else []
        
        fields = {}
        if isinstance(properties, dict):
            for prop_name, prop_val in properties.items():
                if not isinstance(prop_val, dict):
                    continue
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
        clean_model_name = "".join([c if c.isalnum() else "_" for c in self.name])
        self.args_schema = create_model(
            f"{clean_model_name}_args",
            **fields
        )

    def execute(self, sandbox, **kwargs) -> Any:
        """
        Dynamically execute the skill instructions inside the sandbox.
        """
        if not self.brain:
            raise ValueError("Error: Brain dependency must be provided to execute DynamicMarkdownSkill.")

        # Properly format BaseAgentTool schemas to bind to the LLM
        formatted_tools = []
        for t in self.tools:
            if hasattr(t, "name") and hasattr(t, "description") and hasattr(t, "args_schema"):
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.args_schema.model_json_schema()
                    }
                })
            else:
                formatted_tools.append(t)

        llm = self.brain.get_model().bind_tools(formatted_tools)
        
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

class MarkdownSkill(DynamicMarkdownSkill):
    """
    Legacy wrapper for MarkdownSkill to support backward compatibility in existing tests.
    """
    pass
