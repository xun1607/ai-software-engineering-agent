from typing import List, Dict, Any
from .base import AbstractFilterStrategy

class ConstraintFilterStrategy(AbstractFilterStrategy):
    """
    Filters skills based on physical constraints:
    - OS compatibility
    - RAM availability
    - Session Blacklist (from previous failures)
    """
    def filter(self, skills: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        env = context.get("environment", {})
        blacklist = context.get("temporary_blacklist", [])
        current_os = env.get("os_name")
        avail_ram = env.get("available_ram_mb", 0)

        filtered = []
        for skill in skills:
            # 1. Check Session Blacklist
            if skill["name"] in blacklist:
                continue

            constraints = skill.get("constraints", {})
            
            # 2. Check OS Compatibility
            required_os = constraints.get("host", {}).get("os", [])
            if required_os and current_os not in required_os:
                continue

            # 3. Check Resource Limits (RAM)
            # Example: "128MB" -> 128
            req_mem_str = constraints.get("resources", {}).get("memory", "0MB")
            try:
                req_mem = int(req_mem_str.replace("MB", "").replace("GB", "000"))
                if req_mem > avail_ram:
                    continue
            except ValueError:
                pass # Default to allowing if format is weird

            filtered.append(skill)
        
        return filtered