import json
import os
from typing import List, Dict, Any
from abc import ABC, abstractmethod

class AbstractLongTermMemory(ABC):
    @abstractmethod
    def record_success(self, task: str, solution: str, metadata: Dict[str, Any]):
        pass

    @abstractmethod
    def search_experience(self, query: str) -> List[Dict[str, Any]]:
        pass

class JSONExperienceStore(AbstractLongTermMemory):
    def __init__(self, file_path: str = None):
        if file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            swe_agent_dir = os.path.dirname(current_dir)
            self.file_path = os.path.join(swe_agent_dir, "experience_store.json")
        else:
            self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    def record_success(self, task: str, solution: str, metadata: Dict[str, Any]):
        with open(self.file_path, 'r+') as f:
            data = json.load(f)
            data.append({
                "task": task,
                "solution": solution,
                "metadata": metadata
            })
            f.seek(0)
            json.dump(data, f, indent=4)

    def search_experience(self, query: str) -> List[Dict[str, Any]]:
        # Mock search: Hiện tại trả về toàn bộ kinh nghiệm
        with open(self.file_path, 'r') as f:
            return json.load(f)