
def print_tool(task, state):
    return f"[PRINT] {task.get('description')}"

def file_reader_tool(task, state):
    return "dummy file content"

skill_registry = {
    "print_tool": print_tool,
    "file_reader": file_reader_tool,
}
