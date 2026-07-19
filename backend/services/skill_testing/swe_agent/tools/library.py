from swe_agent.tools.base import BaseAgentTool
from pydantic import BaseModel, Field
import os

class ReadFileInput(BaseModel):
    filename: str = Field(description="The path of the file to read (relative to workspace).")

class ReadFileTool(BaseAgentTool):
    name = "read_file"
    description = "Read the contents of a file from the workspace sandbox."
    args_schema = ReadFileInput

    def execute(self, sandbox, filename: str) -> str:
        try:
            return sandbox.read_file(filename)
        except Exception as e:
            return f"Error reading file: {str(e)}"

class WriteFileInput(BaseModel):
    filename: str = Field(description="The path of the file to write (relative to workspace).")
    content: str = Field(description="The string content to write to the file.")

class WriteFileTool(BaseAgentTool):
    name = "write_file"
    description = "Write or overwrite content of a file in the workspace sandbox."
    args_schema = WriteFileInput

    def execute(self, sandbox, filename: str, content: str) -> str:
        try:
            sandbox.write_file(filename, content)
            return f"Successfully wrote to file '{filename}'."
        except Exception as e:
            return f"Error writing file: {str(e)}"

class TerminalShellInput(BaseModel):
    command: str = Field(description="The shell command to execute in the workspace sandbox.")

class TerminalShellTool(BaseAgentTool):
    name = "terminal_shell"
    description = "Execute a terminal shell command inside the workspace sandbox."
    args_schema = TerminalShellInput

    def execute(self, sandbox, command: str) -> str:
        response = sandbox.execute_command(command)
        if response.exit_code == 0:
            return response.stdout
        else:
            return f"Command failed with exit code {response.exit_code}.\nStdout: {response.stdout}\nStderr: {response.stderr}"

class GrepSearchInput(BaseModel):
    pattern: str = Field(description="The regex or substring pattern to search for.")
    path: str = Field(default=".", description="The relative path/folder to search in.")

class GrepSearchTool(BaseAgentTool):
    name = "grep_search"
    description = "Search for a pattern within files in the workspace sandbox."
    args_schema = GrepSearchInput

    def execute(self, sandbox, pattern: str, path: str = ".") -> str:
        workspace_path = getattr(sandbox, "workspace_path", None)
        if not workspace_path:
            return "Error: Sandbox does not provide workspace_path."
        
        search_root = workspace_path / path
        if not search_root.exists():
            return f"Error: Path '{path}' does not exist."
            
        results = []
        import re
        try:
            for root, _, files in os.walk(search_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    if "__pycache__" in file_path or ".git" in file_path:
                        continue
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if re.search(pattern, line):
                                    rel_path = os.path.relpath(file_path, workspace_path)
                                    results.append(f"{rel_path}:{i}: {line.strip()}")
                                    if len(results) >= 50:
                                        break
                    except Exception:
                        pass
                    if len(results) >= 50:
                        break
            if not results:
                return f"No matches found for pattern '{pattern}'."
            return "\n".join(results[:50])
        except Exception as e:
            return f"Error during grep search: {str(e)}"
