import os
import glob
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
            
    patched_code = args.get("patched_code") or args.get("code_context") or args.get("code_snippet")
    file_path = get_file_path(context.workspace_dir, filename)
    
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
        message=f"[SKILL] Patched Java source file: {filename}"
    )
