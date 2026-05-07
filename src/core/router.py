# semantic router 
def route_skill(task: dict):
    skill = task["skill_id"]
    if skill in ["llm_task", "code_gen", "analysis"]:
        return "llm"
    return "tool"