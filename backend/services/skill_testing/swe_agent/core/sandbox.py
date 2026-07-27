import os
import subprocess
import platform
from typing import Any, Dict
import psutil
import shutil
from pathlib import Path
from .base import AbstractSandbox, SandboxResponse

class LocalSandbox(AbstractSandbox):
    def __init__(self, workspace_dir: str):
        self.workspace_path = Path(workspace_dir).absolute()
        self._prepare_workspace()

    def _prepare_workspace(self):
        if not self.workspace_path.exists():
            self.workspace_path.mkdir(parents=True)

    def execute_command(self, command: str, timeout: int = 60) -> SandboxResponse:
        try:
            # Run command inside the workspace directory with UTF-8 encoding & replace fallback on Windows
            process = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_path),
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            return SandboxResponse(
                stdout=process.stdout or "",
                stderr=process.stderr or "",
                exit_code=process.returncode
            )
        except subprocess.TimeoutExpired as e:
            stdout_str = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode('utf-8', errors='replace') if e.stdout else "")
            return SandboxResponse(
                stdout=stdout_str,
                stderr=f"TimeoutExpired: Command timed out after {timeout}s",
                exit_code=124
            )
        except Exception as e:
            return SandboxResponse(stdout="", stderr=str(e), exit_code=1)

    def write_file(self, path: str, content: str) -> None:
        full_path = self.workspace_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)

    def read_file(self, path: str) -> str:
        full_path = self.workspace_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"File {path} not found in workspace")
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def get_environment_info(self) -> Dict[str, Any]:
        """Provide important data for CASS Ranker/Filter to work."""
        return {
            "os_name": platform.system().lower(),
            "available_ram_mb": psutil.virtual_memory().available // (1024 * 1024),
            "cpu_cores": psutil.cpu_count(logical=False),
            "workspace_root": str(self.workspace_path)
        }