from langchain_openai import ChatOpenAI
import os
from core.state import AgentState
from core.router import route_skill
from temp_skill.skills import skill_registry
import json
# Init LLM
def get_llm():
    return ChatOpenAI(
        model="deepseek-coder",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com",
        temperature=0
    )

llm = get_llm()

def run_task(task, user_input, memory, context: str):
    """
    Thực thi 1 task bằng LLM (giả lập skill execution)
    """
    prompt = f"""
    Bạn là AI software engineer.
    User Request:
    {user_input}
    Ngữ cảnh:
    {context}
    Shared Memory:
    {memory}

    Nhiệm vụ:
    {task['description']}
    Hãy thực hiện nhiệm vụ và trả về kết quả.
    """

    response = llm.invoke(prompt)
    return response.content

# Define executor node
# def executor_node(state: AgentState):
#     step_idx = state["current_step"]
#     if step_idx >= len(state["plan"]):
#         return {"current_step": step_idx}
#     task = state["plan"][step_idx]

#     # lấy memory cũ
#     input_context = state.get("context_data", {})
#     print(f"[Executor] {task['skill_id']}")

#     # truyền toàn bộ state/context vào task
#     result = run_task(
#         task=task,
#         user_input=state["input"],
#         memory=input_context,
#         context="\n".join([f"{k}: {v}" for k, v in input_context.items()])
#     )
#     # update memory
#     new_context = {
#         **input_context,
#         task["id"]: result
#     }

#     return {
#         "results": [{
#         "task_id": task["id"],
#         "skill": task["skill_id"],
#         "output": result
#         }],
#     "context_data": new_context,
#     "current_step": step_idx + 1
#     }


def executor_node(state):
    step_idx = state["current_step"]
    if step_idx >= len(state["plan"]):
        return state

    task = state["plan"][step_idx]
    input_context = state.get("context_data", {})
    print(f"[Executor] Step {step_idx} - {task['skill_id']}")
    skill_type = route_skill(task)

    # -----------------------
    # 1. LLM SKILL
    # -----------------------
    if skill_type == "llm":
        result = run_task(
            task=task,
            user_input=state["input"],
            memory=input_context,
            context=json.dumps(input_context, ensure_ascii=False)
        )

    # -----------------------
    # 2. TOOL SKILL
    # -----------------------
    else:
        handler = skill_registry.get(task["skill_id"])
        if handler:
            result = handler(task, state)
        else:
            result = f"[ERROR] Unknown skill: {task['skill_id']}"

    # update memory
    new_context = {
        **input_context,
        task["id"]: result
    }

    return {
        "results": [{
            "task_id": task["id"],
            "skill": task["skill_id"],
            "output": result
        }],
        "context_data": new_context,
        "current_step": step_idx + 1
    }
