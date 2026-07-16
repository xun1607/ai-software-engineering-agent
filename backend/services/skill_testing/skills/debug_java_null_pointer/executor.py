import os
import glob
import asyncio
from services.skill_testing.core.execution_models import ExecutionContext, SkillResult

def get_file_path(workspace_dir: str, filename: str) -> str:
    if not filename:
        return ""
    if "src/main/java" in filename or filename.startswith("/") or ":" in filename or filename.startswith("."):
        return os.path.join(workspace_dir, filename)
    if filename.endswith(".java"):
        return os.path.join(workspace_dir, "src", "main", "java", filename)
    return os.path.join(workspace_dir, filename)

async def execute(context: ExecutionContext, args: dict) -> SkillResult:
    filename = args.get("file") or args.get("source_path")
    if not filename:
        java_src_dir = os.path.join(context.workspace_dir, "src", "main", "java")
        java_files = glob.glob(os.path.join(java_src_dir, "*.java"))
        if java_files:
            filename = os.path.basename(java_files[0])
        else:
            filename = "LoginService.java"
            
    file_path = get_file_path(context.workspace_dir, filename)
    rel_file_path = os.path.relpath(file_path, context.workspace_dir)
    
    # Sử dụng asyncio.create_subprocess_exec để chạy bất đồng bộ 
    proc = await asyncio.create_subprocess_exec(
        "javac", rel_file_path,
        cwd=context.workspace_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Đăng ký tiến trình con vào context để Runtime Layer kiểm soát
    context.register_process(proc)
    try:
        stdout_bytes, stderr_bytes = await proc.communicate()
    finally:
        context.unregister_process(proc)
        
    stdout = stdout_bytes.decode("utf-8", errors="ignore")
    stderr = stderr_bytes.decode("utf-8", errors="ignore")
    
    if proc.returncode == 0:
        return SkillResult(
            status="SUCCESS",
            stdout=stdout,
            stderr=stderr,
            message=f"Javac compiled {filename} successfully.",
            data={"returncode": proc.returncode}
        )
    else:
        return SkillResult(
            status="FAILED",
            stdout=stdout,
            stderr=stderr,
            message=f"Compilation failed for {filename}.",
            data={"returncode": proc.returncode}
        )
