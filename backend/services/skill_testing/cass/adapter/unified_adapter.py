import inspect
from typing import Any, Callable, Dict, List, get_type_hints, Literal

class UnifiedSkillAdapter:
    """
    Standardizes Python functions into the CASS Skill Schema.
    Maps metadata to the SKILL.md structure (YAML frontmatter).
    """

    @staticmethod
    def python_to_cass_profile(
        func: Callable, 
        category: str = "universal/generic",
        tags: List[str] = None,
        overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Inspects a function to generate a full CASS metadata profile.
        """
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # Extract properties for Input JSON Schema
        properties = {}
        required = []

        for name, param in signature.parameters.items():
            if name in ("self", "cls"): continue
            
            p_type = type_hints.get(name, Any)
            type_str = UnifiedSkillAdapter._map_type(p_type)
            
            properties[name] = {
                "type": type_str,
                "description": f"Input parameter {name}"
            }
            if param.default == inspect.Parameter.empty:
                required.append(name)

        # Build full CASS Schema structure
        profile = {
            "name": func.__name__.replace("_", "-"),
            "description": (func.__doc__ or "No description provided").strip(),
            "version": "1.0.0",
            "category": category,
            "level": "atomic",
            "tags": tags or [],
            "input": {
                "type": "object",
                "required": required,
                "properties": properties
            },
            "output": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "status": {"type": "string"}
                }
            },
            "constraints": {
                "host": {
                    "os": [], # Empty means cross-platform
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

        # Apply nested overrides using deep merge
        if overrides:
            def deep_merge(target: dict, source: dict):
                for k, v in source.items():
                    if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                        deep_merge(target[k], v)
                    else:
                        target[k] = v
            deep_merge(profile, overrides)
        
        return profile
        

    @staticmethod
    def _map_type(python_type: Any) -> str:
        """Maps Python types to JSON Schema primitive types."""
        mapping = {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        return mapping.get(python_type, "string")