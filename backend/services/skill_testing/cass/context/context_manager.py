import platform
import psutil
from typing import Dict, Any, Set, Optional

class CASSContextManager:
    """
    Observer for the execution environment and session state.
    Provides data to filter skills that are physically incompatible.
    """

    def __init__(self):
        # Cache static OS info to minimize system calls
        self._static_info = self._get_os_info()
        self._session_blacklist: Dict[str, Set[str]] = {}

    def _get_os_info(self) -> Dict[str, Any]:
        """Captures hardware and OS specs."""
        return {
            "os_name": platform.system().lower(),  # e.g., 'linux', 'windows', 'darwin'
            "cpu_cores": psutil.cpu_count(logical=False),
            "total_ram_mb": psutil.virtual_memory().total // (1024 * 1024)
        }

    def register_session_failure(self, session_id: str, skill_name: str):
        """Temporarily blacklists a skill for the current session."""
        if session_id not in self._session_blacklist:
            self._session_blacklist[session_id] = set()
        self._session_blacklist[session_id].add(skill_name)

    def get_full_context(self, session_id: str, subtask: str) -> Dict[str, Any]:
        """
        Builds the context object used by the Filter Layer.
        Includes hardware status and session-specific blacklists.
        """
        mem = psutil.virtual_memory()
        return {
            "session_id": session_id,
            "current_subtask": subtask,
            "environment": {
                **self._static_info,
                "available_ram_mb": mem.available // (1024 * 1024)
            },
            "temporary_blacklist": list(self._session_blacklist.get(session_id, []))
        }