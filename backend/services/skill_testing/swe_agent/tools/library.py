from swe_agent.tools.base import BaseAgentTool
from pydantic import BaseModel, Field
import os
import re
import fnmatch
from pathlib import Path

# --- READ FILE TOOL ---
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

# --- WRITE FILE TOOL ---
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

# --- EDIT FILE TOOL ---
class EditFileInput(BaseModel):
    filename: str = Field(description="The path of the file to edit (relative to workspace).")
    old_str: str = Field(description="The exact block of text in the file to be replaced.")
    new_str: str = Field(description="The new block of text to replace it with.")

class EditFileTool(BaseAgentTool):
    name = "edit_file"
    description = "Replace a specific text block in a file with new content."
    args_schema = EditFileInput

    def execute(self, sandbox, filename: str, old_str: str, new_str: str) -> str:
        try:
            content = sandbox.read_file(filename)
            if old_str not in content:
                return f"Error: The target text block to replace ('old_str') was not found in '{filename}'."
            
            occurrences = content.count(old_str)
            new_content = content.replace(old_str, new_str)
            sandbox.write_file(filename, new_content)
            
            msg = f"Successfully updated '{filename}'."
            if occurrences > 1:
                msg += f" Replaced all {occurrences} occurrences of the target text."
            else:
                msg += " Replaced 1 occurrence of the target text."
            return msg
        except Exception as e:
            return f"Error editing file '{filename}': {str(e)}"

# --- LIST FILES TOOL ---
class ListFilesInput(BaseModel):
    path: str = Field(default=".", description="The relative path of the directory to list (relative to workspace).")

class ListFilesTool(BaseAgentTool):
    name = "list_files"
    description = "List all files and directories in the specified relative path in the workspace."
    args_schema = ListFilesInput

    def execute(self, sandbox, path: str = ".") -> str:
        workspace_path = getattr(sandbox, "workspace_path", None)
        if not workspace_path:
            return "Error: Sandbox does not provide workspace_path."
        try:
            target_path = Path(workspace_path / path).resolve()
            real_workspace = Path(workspace_path).resolve()
            
            # ensure path is within workspace
            if not str(target_path).startswith(str(real_workspace)):
                return "Error: Access denied (path outside of workspace)."
            
            if not target_path.exists():
                return f"Error: Path '{path}' does not exist."
            
            if not target_path.is_dir():
                return f"Error: Path '{path}' is a file, not a directory."
            
            items = os.listdir(target_path)
            results = []
            for item in sorted(items):
                item_path = target_path / item
                is_dir = "[DIR]" if item_path.is_dir() else "[FILE]"
                size = "" if item_path.is_dir() else f" ({item_path.stat().st_size} bytes)"
                results.append(f"{is_dir} {item}{size}")
                
            if not results:
                return f"Directory '{path}' is empty."
            return "\n".join(results)
        except Exception as e:
            return f"Error listing directory '{path}': {str(e)}"

# --- FIND FILE TOOL ---
class FindFileInput(BaseModel):
    pattern: str = Field(description="The glob pattern or substring to search for in filenames (e.g. '*.py' or 'validator').")
    path: str = Field(default=".", description="The relative path/folder to search in (relative to workspace).")

class FindFileTool(BaseAgentTool):
    name = "find_file"
    description = "Find files by name pattern in the workspace sandbox."
    args_schema = FindFileInput

    def execute(self, sandbox, pattern: str, path: str = ".") -> str:
        workspace_path = getattr(sandbox, "workspace_path", None)
        if not workspace_path:
            return "Error: Sandbox does not provide workspace_path."
        try:
            search_root = Path(workspace_path / path).resolve()
            real_workspace = Path(workspace_path).resolve()
            if not str(search_root).startswith(str(real_workspace)):
                return "Error: Access denied (path outside of workspace)."
                
            if not search_root.exists():
                return f"Error: Path '{path}' does not exist."

            matches = []
            for root, _, files in os.walk(search_root):
                for file in files:
                    if fnmatch.fnmatch(file, pattern) or pattern in file:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, workspace_path)
                        rel_path = rel_path.replace(os.sep, "/")
                        matches.append(rel_path)
                        if len(matches) >= 50:
                            break
                if len(matches) >= 50:
                    break
            
            if not matches:
                return f"No files found matching pattern '{pattern}' in '{path}'."
            return "\n".join(matches)
        except Exception as e:
            return f"Error finding files: {str(e)}"

# --- SEARCH CODE TOOL ---
class SearchCodeInput(BaseModel):
    pattern: str = Field(description="The regex or substring pattern to search for inside file contents.")
    path: str = Field(default=".", description="The relative path/folder to search in (relative to workspace).")

class SearchCodeTool(BaseAgentTool):
    name = "search_code"
    description = "Search for a pattern within file contents in the workspace sandbox."
    args_schema = SearchCodeInput

    def execute(self, sandbox, pattern: str, path: str = ".") -> str:
        workspace_path = getattr(sandbox, "workspace_path", None)
        if not workspace_path:
            return "Error: Sandbox does not provide workspace_path."
        
        try:
            search_root = Path(workspace_path / path).resolve()
            real_workspace = Path(workspace_path).resolve()
            if not str(search_root).startswith(str(real_workspace)):
                return "Error: Access denied (path outside of workspace)."
                
            if not search_root.exists():
                return f"Error: Path '{path}' does not exist."
                
            results = []
            for root, _, files in os.walk(search_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    if any(ignored in file_path for ignored in ["__pycache__", ".git", ".venv", ".pytest_cache", "node_modules"]):
                        continue
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if re.search(pattern, line):
                                    rel_path = os.path.relpath(file_path, workspace_path)
                                    rel_path = rel_path.replace(os.sep, "/")
                                    results.append(f"{rel_path}:{i}: {line.strip()}")
                                    if len(results) >= 50:
                                        break
                    except Exception:
                        pass
                    if len(results) >= 50:
                        break
            
            if not results:
                return f"No matches found for pattern '{pattern}' in '{path}'."
            return "\n".join(results[:50])
        except Exception as e:
            return f"Error during code search: {str(e)}"

# --- GREP SEARCH TOOL (Legacy support) ---
class GrepSearchInput(BaseModel):
    pattern: str = Field(description="The regex or substring pattern to search for.")
    path: str = Field(default=".", description="The relative path/folder to search in.")

class GrepSearchTool(BaseAgentTool):
    name = "grep_search"
    description = "Search for a pattern within files in the workspace sandbox."
    args_schema = GrepSearchInput

    def execute(self, sandbox, pattern: str, path: str = ".") -> str:
        # Delegate directly to SearchCodeTool for unified logic
        search_tool = SearchCodeTool()
        return search_tool.execute(sandbox, pattern, path)

# --- TERMINAL SHELL TOOL ---
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

# --- RUN TESTS TOOL ---
class RunTestsInput(BaseModel):
    test_cmd: str = Field(default="", description="The test command to run (e.g. 'pytest tests/'). If empty, auto-detects based on project type.")

class RunTestsTool(BaseAgentTool):
    name = "run_tests"
    description = "Execute tests within the workspace sandbox and return results."
    args_schema = RunTestsInput

    def execute(self, sandbox, test_cmd: str = "") -> str:
        try:
            if not test_cmd:
                workspace_path = getattr(sandbox, "workspace_path", None)
                if workspace_path:
                    ws = Path(workspace_path)
                    if (ws / "pytest.ini").exists() or (ws / "tests").exists() or any(ws.glob("**/test_*.py")):
                        test_cmd = "pytest"
                    elif (ws / "pom.xml").exists():
                        test_cmd = "mvn test"
                    elif (ws / "build.gradle").exists():
                        test_cmd = "./gradlew test"
                    else:
                        test_cmd = "python -m unittest"
                else:
                    test_cmd = "python -m unittest"

            response = sandbox.execute_command(test_cmd)
            if response.exit_code == 0:
                return f"Tests passed successfully (exit code 0)!\nStdout:\n{response.stdout}"
            else:
                return f"Tests failed with exit code {response.exit_code}.\nStdout:\n{response.stdout}\nStderr:\n{response.stderr}"
        except Exception as e:
            return f"Error running tests: {str(e)}"

# --- COMPILE PROJECT TOOL ---
class CompileProjectInput(BaseModel):
    compile_cmd: str = Field(default="", description="The compilation command to run (e.g. 'mvn compile', 'javac src/main/java/*.java'). If empty, auto-detects project type.")

class CompileProjectTool(BaseAgentTool):
    name = "compile_project"
    description = "Compile the project codebase in the workspace sandbox."
    args_schema = CompileProjectInput

    def execute(self, sandbox, compile_cmd: str = "") -> str:
        try:
            if not compile_cmd:
                workspace_path = getattr(sandbox, "workspace_path", None)
                if workspace_path:
                    ws = Path(workspace_path)
                    if (ws / "pom.xml").exists():
                        compile_cmd = "mvn compile"
                    elif (ws / "build.gradle").exists():
                        compile_cmd = "./gradlew compileJava"
                    elif any(ws.glob("**/*.java")):
                        compile_cmd = "javac src/main/java/*.java"
                    else:
                        return "No compilation step is required or detected for this project type."
                else:
                    return "No compilation step is required or detected for this project type."

            response = sandbox.execute_command(compile_cmd)
            if response.exit_code == 0:
                return f"Project compiled successfully (exit code 0)!\nStdout:\n{response.stdout}"
            else:
                return f"Compilation failed with exit code {response.exit_code}.\nStdout:\n{response.stdout}\nStderr:\n{response.stderr}"
        except Exception as e:
            return f"Error compiling project: {str(e)}"

# --- GIT DIFF TOOL ---
class GitDiffInput(BaseModel):
    path: str = Field(default=".", description="Optional relative path to show diff for (default is workspace root).")

class GitDiffTool(BaseAgentTool):
    name = "git_diff"
    description = "View changes made in the workspace repository using git diff."
    args_schema = GitDiffInput

    def execute(self, sandbox, path: str = ".") -> str:
        try:
            workspace_path = getattr(sandbox, "workspace_path", None)
            if workspace_path:
                target_path = Path(workspace_path / path).resolve()
                real_workspace = Path(workspace_path).resolve()
                if not str(target_path).startswith(str(real_workspace)):
                    return "Error: Access denied (path outside of workspace)."

            response = sandbox.execute_command(f"git diff {path}")
            if response.exit_code == 0:
                diff_output = response.stdout.strip()
                if not diff_output:
                    return "No changes detected in git workspace."
                return diff_output
            else:
                return f"git diff failed (exit code {response.exit_code}). Make sure git is initialized.\nStderr: {response.stderr}"
        except Exception as e:
            return f"Error executing git diff: {str(e)}"
