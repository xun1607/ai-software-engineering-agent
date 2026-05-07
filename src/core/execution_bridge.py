from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.skill_selector import SkillSelector


SkillHandler = Callable[[Dict[str, Any], Dict[str, Any]], Any]


class ExecutionBridge:
    """AG2 boundary for selecting and invoking AG1 skills."""

    def __init__(self, skills_dir: str | Path | None = None, use_llm: Optional[bool] = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).resolve().parents[2] / "skills"
        self.use_llm = self._should_use_llm(use_llm)
        self._registry = None
        self._executor = None
        self._built_in_skills: Dict[str, SkillHandler] = {
            "file-reader-skill": self._read_file_or_inline_code,
            "code-parser-skill": self._parse_code_from_memory,
            "test-case-identifier-skill": self._identify_test_cases,
            "code-writer-skill": self._write_code_from_memory,
            "code-fixer-skill": self._fix_code_error,
            "llm-software-engineer-skill": self._general_llm_skill,
            "debug-java-null-pointer": self._general_llm_skill,
        }
        self._load_ag1()
        self.selector = SkillSelector(self._registry, self._built_in_skills)

    def execute(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        self._last_token_estimate = 0
        selection = self.selector.select(task)
        skill_id = selection.skill_id
        if not skill_id:
            return {
                "success": False,
                "skill_id": None,
                "selection": selection.to_dict(),
                "output": None,
                "error": f"No AG1 skill found for capability: {task.get('capability')}",
                "token_usage": 0,
            }

        handler = self._built_in_skills.get(skill_id)
        if handler:
            try:
                output = handler(task, prepared_input)
                return {
                    "success": True,
                    "skill_id": skill_id,
                    "selection": selection.to_dict(),
                    "output": output,
                    "error": None,
                    "token_usage": self._last_token_estimate,
                }
            except Exception as exc:
                return self._failure(skill_id, selection.to_dict(), exc)

        if self._registry and self._executor:
            skill = self._registry.get(skill_id)
            if skill:
                try:
                    output = self._executor.run(skill, prepared_input)
                    return {
                        "success": True,
                        "skill_id": skill_id,
                        "selection": selection.to_dict(),
                        "output": output,
                        "error": None,
                        "token_usage": self._last_token_estimate,
                    }
                except Exception as exc:
                    return self._failure(skill_id, selection.to_dict(), exc)

        return {
            "success": False,
            "skill_id": skill_id,
            "selection": selection.to_dict(),
            "output": None,
            "error": f"Selected skill is not executable: {skill_id}",
            "token_usage": 0,
        }

    def _read_file_or_inline_code(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        user_input = prepared_input.get("user_input", "")
        path = prepared_input.get("facts", {}).get("file_path") or self._extract_file_path(user_input)
        if path:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            content = file_path.read_text(encoding="utf-8")
            return {"source": str(file_path), "content": content}

        code = self._extract_inline_code(user_input)
        return {"source": "user_input", "content": code or user_input}

    def _parse_code_from_memory(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        previous = prepared_input.get("dependency_outputs", {})
        read_result = previous.get("read-file") or prepared_input.get("last_output") or {}
        content = read_result.get("content", "") if isinstance(read_result, dict) else str(read_result)

        try:
            tree = ast.parse(content)
            functions = [
                {"name": node.name, "args": [arg.arg for arg in node.args.args]}
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ]
            language = "python"
        except SyntaxError:
            functions = [{"name": name, "args": []} for name in re.findall(r"\b(\w+)\s*\([^)]*\)\s*\{", content)]
            language = "unknown"

        if not functions and prepared_input.get("retry_count", 0) > 0:
            functions = [{"name": "target_function", "args": []}]
            language = "recovered"

        return {
            "language": language,
            "functions": functions,
            "content_preview": content[:500],
        }

    def _identify_test_cases(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        prompt = "Identify concise unit test cases from the parsed code metadata."
        llm_output = self._invoke_llm_skill(task, prepared_input, prompt)
        if llm_output:
            return {"test_cases": llm_output}

        parsed = prepared_input.get("dependency_outputs", {}).get("extract-metadata", {})
        functions = parsed.get("functions", []) if isinstance(parsed, dict) else []
        cases = []
        for function in functions or [{"name": "target_function"}]:
            name = function.get("name", "target_function")
            cases.extend([f"{name}: normal input", f"{name}: edge input", f"{name}: invalid input"])
        return {"test_cases": cases}

    def _write_code_from_memory(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        prompt = "Write implementation or test code using the available context memory."
        llm_output = self._invoke_llm_skill(task, prepared_input, prompt)
        if llm_output:
            return {"code": llm_output}

        test_cases = prepared_input.get("dependency_outputs", {}).get("identify_test_cases", {}).get("test_cases", [])
        lines = ["# Generated test skeleton", "def test_generated_behavior():", "    # Cases: " + ", ".join(test_cases), "    assert True"]
        return {"code": "\n".join(lines)}

    def _general_llm_skill(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        prompt = "Act as the requested software engineering skill and solve the task."
        output = self._invoke_llm_skill(task, prepared_input, prompt)
        return {"answer": output or f"LLM skill fallback for task: {task.get('description')}"}

    def _fix_code_error(self, task: Dict[str, Any], prepared_input: Dict[str, Any]) -> Dict[str, Any]:
        prompt = "Fix the previous code or execution error using the retry context."
        output = self._invoke_llm_skill(task, prepared_input, prompt)
        return {"fixed_code": output or prepared_input.get("retry_instruction") or "No retry context supplied."}

    def _invoke_llm_skill(self, task: Dict[str, Any], prepared_input: Dict[str, Any], instruction: str) -> Optional[str]:
        if not self.use_llm:
            return None

        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=0,
        )
        prompt = (
            f"{instruction}\n\n"
            f"Retry instruction:\n{prepared_input.get('retry_instruction', '')}\n\n"
            f"Task:\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
            f"Prepared memory input:\n{json.dumps(prepared_input, ensure_ascii=False, indent=2, default=str)}"
        )
        response = llm.invoke(prompt).content
        self._last_token_estimate += max(1, len(prompt.split()) + len(str(response).split()))
        return response

    def _load_ag1(self) -> None:
        try:
            from data.skill_library.core.executor import SkillExecutor
            from data.skill_library.core.registry import SkillRegistry

            registry = SkillRegistry(self.skills_dir)
            registry.load_all()
            self._registry = registry
            self._executor = SkillExecutor(registry, mock_mode=True)
        except Exception:
            self._registry = None
            self._executor = None

    @staticmethod
    def _should_use_llm(use_llm: Optional[bool]) -> bool:
        if use_llm is not None:
            return use_llm
        return os.getenv("AG2_USE_LLM_SKILLS", "").lower() in {"1", "true", "yes"} and bool(os.getenv("DEEPSEEK_API_KEY"))

    @staticmethod
    def _failure(skill_id: str, selection: Dict[str, Any], exc: Exception) -> Dict[str, Any]:
        return {
            "success": False,
            "skill_id": skill_id,
            "selection": selection,
            "output": None,
            "error": str(exc),
            "token_usage": 0,
        }

    @staticmethod
    def _extract_file_path(user_input: str) -> Optional[str]:
        match = re.search(r"(?:file|path)\s*[:=]\s*([^\s]+)", user_input, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _extract_inline_code(user_input: str) -> str:
        fenced = re.search(r"```(?:\w+)?\s*(.*?)```", user_input, re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        return user_input
