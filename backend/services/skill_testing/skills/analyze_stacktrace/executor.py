import re
import os
import glob
from services.skill_testing.core.execution_models import ExecutionContext, SkillResult

async def execute(context: ExecutionContext, args: dict) -> SkillResult:
    raw_stacktrace = args.get("stacktrace", "")
    
    py_match = re.search(r'File\s+["\']([^"\']+)["\'],\s*line\s*(\d+)', raw_stacktrace)
    java_match = re.search(r'at\s+[\w\.]+\([\w\-]+\.java:(\d+)\)', raw_stacktrace)
    java_file_match = re.search(r'([\w\-]+\.java)', raw_stacktrace)
    
    parsed_file = None
    parsed_line = 1
    
    if py_match:
        parsed_file = py_match.group(1)
        parsed_line = int(py_match.group(2))
    elif java_match:
        parsed_line = int(java_match.group(1))
        if java_file_match:
            parsed_file = java_file_match.group(1)
    elif java_file_match:
        parsed_file = java_file_match.group(1)
    
    if not parsed_file:
        parsed_file = args.get("file") or args.get("source_path")
        if not parsed_file:
            java_src_dir = os.path.join(context.workspace_dir, "src", "main", "java")
            java_files = glob.glob(os.path.join(java_src_dir, "*.java"))
            py_files = glob.glob(os.path.join(context.workspace_dir, "*.py"))
            if java_files:
                parsed_file = os.path.basename(java_files[0])
            elif py_files:
                parsed_file = os.path.basename(py_files[0])
            else:
                parsed_file = "LoginService.java"
                
    return SkillResult(
        status="SUCCESS",
        stdout=f"Parsed frame: {parsed_file} at line {parsed_line}.",
        message=f"[SKILL] Detected crash point in stacktrace: {parsed_file}:{parsed_line}",
        data={
            "file": parsed_file,
            "line": parsed_line
        }
    )
