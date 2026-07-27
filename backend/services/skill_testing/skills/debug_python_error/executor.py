import os
import sys
import glob
import asyncio
from services.skill_testing.core.execution_models import ExecutionContext, SkillResult

async def execute(context: ExecutionContext, args: dict) -> SkillResult:
    filename = args.get("file") or args.get("source_path")
    if not filename:
        py_files = glob.glob(os.path.join(context.workspace_dir, "*.py"))
        if py_files:
            filename = os.path.basename(py_files[0])
        else:
            filename = "data_sync.py"
            
    if not filename.endswith(".py"):
        filename += ".py"
        
    file_path = os.path.join(context.workspace_dir, filename)
    
    python_exe = os.path.join(os.path.dirname(context.workspace_dir), "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable  # Fallback to current python interpreter
        
    proc = await asyncio.create_subprocess_exec(
        python_exe, filename,
        cwd=context.workspace_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
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
            message=f"Python script {filename} executed successfully.",
            data={"returncode": proc.returncode}
        )
    else:
        return SkillResult(
            status="FAILED",
            stdout=stdout,
            stderr=stderr,
            message=f"Python execution failed for {filename}.",
            data={"returncode": proc.returncode}
        )
