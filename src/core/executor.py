from langchain_openai import ChatOpenAI
import os

# Init LLM
def get_llm():
    return ChatOpenAI(
        model="deepseek-coder",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com",
        temperature=0
    )

llm = get_llm()

def run_task(task: dict, context: str) -> str:
    """
    Thực thi 1 task bằng LLM (giả lập skill execution)
    """
    prompt = f"""
    Bạn là AI software engineer.
    Ngữ cảnh:
    {context}
    Nhiệm vụ:
    {task['description']}
    Hãy thực hiện nhiệm vụ và trả về kết quả.
    """

    response = llm.invoke(prompt)
    return response.content

# Define executor node
def executor_node(state):
    step_idx = state["current_step"]
    task = state["plan"][step_idx]

    print(f"[Executor] {task['skill_id']}")

    result = run_task(task, state["input"])

    return {
        "results": [{
        "task_id": task["id"],
        "skill": task["skill_id"],
        "output": result
    }],
    "current_step": step_idx + 1
    }
    
