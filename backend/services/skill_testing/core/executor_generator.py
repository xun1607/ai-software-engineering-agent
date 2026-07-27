import os
import sys
import yaml
import re
import asyncio
from services.skill_testing.core.llm_client import OpenAIClient

FALLBACK_TEMPLATE = """import os
import asyncio
from services.skill_testing.core.execution_models import ExecutionContext, SkillResult

async def execute(context: ExecutionContext, args: dict) -> SkillResult:
    \"\"\"
    Executor for skill: {name}
    Description: {description}
    
    Input parameters:
{input_params}
    \"\"\"
    # TODO: Implement the custom execution logic here.
    # If running subprocesses:
    # proc = await asyncio.create_subprocess_exec("cmd", "arg1", cwd=context.workspace_dir, stdout=asyncio.subprocess.PIPE)
    # context.register_process(proc)
    # try:
    #     stdout_bytes, stderr_bytes = await proc.communicate()
    # finally:
    #     context.unregister_process(proc)
    
    return SkillResult(
        status="SUCCESS",
        stdout="Template execution completed.",
        message="Executor scaffolded successfully. Implement your custom logic."
    )
"""

async def generate_executor(skill_path_or_name: str):
    # Xác định đường dẫn thư mục skills trực tiếp từ vị trí của file này
    skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills"))
    
    if os.path.exists(skill_path_or_name):
        skill_dir = os.path.abspath(skill_path_or_name)
    else:
        skill_dir = os.path.join(skills_dir, skill_path_or_name)
        
    if not os.path.exists(skill_dir):
        print(f"❌ [GENERATOR] Thư mục kỹ năng không tồn tại: {skill_dir}")
        return
        
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md_path):
        print(f"❌ [GENERATOR] Không tìm thấy file SKILL.md tại: {skill_md_path}")
        return
        
    print(f"🔍 [GENERATOR] Đang đọc cấu trúc SOP từ: {skill_md_path}")
    with open(skill_md_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        print("❌ [GENERATOR] File SKILL.md không có YAML frontmatter hợp lệ.")
        return
        
    yaml_block = match.group(1)
    instructions = match.group(2).strip()
    metadata = yaml.safe_load(yaml_block) or {}
    
    name = metadata.get("name", os.path.basename(skill_dir))
    desc = metadata.get("description", "")
    input_schema = metadata.get("input", {})
    
    # Chuẩn bị thông tin input parameters
    input_params_str = ""
    for k, v in input_schema.items():
        param_type = v.get("type", "any")
        param_desc = v.get("description", "")
        required = " (bắt buộc)" if v.get("required", False) else " (tùy chọn)"
        input_params_str += f"    - {k} ({param_type}){required}: {param_desc}\n"
        
    executor_path = os.path.join(skill_dir, "executor.py")
    
    # Nạp API Key để dùng LLM sinh mã gợi ý
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv, find_dotenv
            load_dotenv(find_dotenv())
            api_key = os.getenv("OPENAI_API_KEY")
        except Exception:
            pass
            
    code_content = None
    if api_key:
        print("🤖 [GENERATOR] Đã phát hiện API_KEY. Đang gọi LLM sinh logic code thực thi mẫu...")
        llm = OpenAIClient(api_key=api_key)
        
        system_prompt = """
        You are a Senior Software Engineer. Your task is to write a Python module 'executor.py' for an AI Agent skill plugin.
        
        The signature of the function MUST be:
        async def execute(context: ExecutionContext, args: dict) -> SkillResult:
        
        CRITICAL IMPORT RULES:
        You MUST import ExecutionContext and SkillResult from 'services.skill_testing.core.execution_models'.
        Do NOT define custom classes for ExecutionContext or SkillResult locally in the file.
        
        You must use the ExecutionContext (which has 'workspace_dir', and methods 'register_process(proc)', 'unregister_process(proc)', 'kill_active_processes()') and return a SkillResult.
        
        CRITICAL RULES:
        1. Do NOT wrap execution in a global try-except or timeout block (the Runtime Layer handles timeouts and unexpected exceptions).
        2. If you need to run shell commands or subprocesses, use `asyncio.create_subprocess_exec` and register/unregister the process in the context.
        3. Return a SkillResult(status="SUCCESS" or "FAILED", stdout=..., stderr=..., message=..., data=...).
        4. Write clean, complete, runnable python code. Do not output markdown blocks or conversational text, output ONLY valid python code. Do NOT wrap code in ```python blocks.
        """
        
        user_prompt = f"""
        SKILL METADATA:
        Name: {name}
        Description: {desc}
        Input parameters: {input_schema}
        
        SOP INSTRUCTIONS (SOP details to implement):
        {instructions}
        """
        
        try:
            raw_code = await llm.call(system_prompt, user_prompt)
            cleaned_code = raw_code.strip()
            if cleaned_code.startswith("```python"):
                cleaned_code = cleaned_code.replace("```python", "", 1)
            if cleaned_code.endswith("```"):
                cleaned_code = cleaned_code[:-3]
            code_content = cleaned_code.strip()
        except Exception as e:
            print(f"⚠️ [GENERATOR WARNING] Lỗi khi gọi LLM: {e}. Chuyển sang fallback bằng Template tĩnh.")
            
    if not code_content:
        print("📝 [GENERATOR] Đang sinh mã bằng Template tĩnh...")
        code_content = FALLBACK_TEMPLATE.format(
            name=name,
            description=desc,
            input_params=input_params_str.rstrip()
        )
        
    with open(executor_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(code_content)
        
    print(f"🎉 [GENERATOR] Khởi tạo thành công bộ thực thi tại: {executor_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m services.skill_testing.core.executor_generator <skill_folder_path_or_name>")
        sys.exit(1)
        
    asyncio.run(generate_executor(sys.argv[1]))
