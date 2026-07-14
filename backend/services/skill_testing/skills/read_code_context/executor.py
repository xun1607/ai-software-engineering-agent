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
        py_files = glob.glob(os.path.join(context.workspace_dir, "*.py"))
        if java_files:
            filename = os.path.basename(java_files[0])
        elif py_files:
            filename = os.path.basename(py_files[0])
        else:
            filename = "LoginService.java"
            
    target_line = int(args.get("line", 1))
    file_path = get_file_path(context.workspace_dir, filename)
    
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = max(0, target_line - 6)
    end = min(len(lines), target_line + 5)
    code_snippet = "".join(lines[start:end])
    
    return SkillResult(
        status="SUCCESS",
        stdout=code_snippet,
        message=f"[SKILL] Read source code context from {filename} around line {target_line}"
    )
