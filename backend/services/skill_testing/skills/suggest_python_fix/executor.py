import os
import glob
from services.skill_testing.core.execution_models import ExecutionContext, SkillResult

async def execute(context: ExecutionContext, args: dict) -> SkillResult:
    filename = args.get("file") or args.get("source_path")
    if not filename:
        py_files = glob.glob(os.path.join(context.workspace_dir, "*.py"))
        if py_files:
            filename = os.path.basename(py_files[0])
        else:
            filename = "data_sync.py"
            
    patched_code = args.get("patched_code") or args.get("code_context") or args.get("code_snippet")
    file_path = os.path.join(context.workspace_dir, filename)
    
    if not patched_code:
        return SkillResult(
            status="FAILED",
            stderr="Missing patched_code parameter.",
            message="Error: Missing patched_code parameter."
        )
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(patched_code)
        
    return SkillResult(
        status="SUCCESS",
        stdout="File updated successfully.",
        message=f"[SKILL] Patched Python source file: {filename}"
    )
