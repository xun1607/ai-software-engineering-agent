from typing import Any, Dict, List

class LangChainCASSAdapter:
    """
    Adapter to convert LangChain tools to CASS Profiles.
    """
    @staticmethod
    def to_cass_profile(tool: Any) -> Dict[str, Any]:
        """
        Converts a LangChain tool object into a standard CASS Skill Profile dict.
        """
        name = getattr(tool, "name", getattr(tool, "__name__", "unknown-tool")).replace("_", "-")
        description = getattr(tool, "description", getattr(tool, "__doc__", "No description provided")) or "No description provided"
        
        args = {}
        required = []
        if hasattr(tool, "args"):
            args = tool.args
            
            # Find required args from arg schema
            if hasattr(tool, "args_schema") and tool.args_schema is not None:
                schema = tool.args_schema
                if hasattr(schema, "model_fields"):
                    for field_name, field in schema.model_fields.items():
                        if field.is_required():
                            required.append(field_name)
                elif hasattr(schema, "__fields__"):
                    for field_name, field in schema.__fields__.items():
                        if field.required:
                            required.append(field_name)
            else:
                required = list(args.keys())

        # Format input schema properties
        properties = {}
        for k, v in args.items():
            if isinstance(v, dict):
                properties[k] = {
                    "type": v.get("type", "string"),
                    "description": v.get("description", f"Input parameter {k}")
                }
            else:
                properties[k] = {
                    "type": "string",
                    "description": f"Input parameter {k}"
                }

        return {
            "name": name,
            "description": description.strip(),
            "version": "1.0.0",
            "category": "langchain/tool",
            "level": "atomic",
            "tags": [],
            "input": {
                "type": "object",
                "required": required,
                "properties": properties
            },
            "output": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"}
                }
            },
            "constraints": {
                "host": {
                    "os": [],
                    "runtimes": ["python3"],
                    "binaries": []
                },
                "resources": {
                    "memory": "128MB",
                    "cpu_cores": 1,
                    "timeout": 60,
                    "network": True
                },
                "safety": {
                    "fs_access": "read-only",
                    "db_access": False,
                    "requires_approval": False
                }
            }
        }
