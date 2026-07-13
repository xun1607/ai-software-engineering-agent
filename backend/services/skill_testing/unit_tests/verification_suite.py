import asyncio
import json
import os
import re
import shutil
import time
import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.core.skill_client import SkillExecutionClient
from services.skill_testing.core.llm_client import OpenAIClient
from services.skill_testing.core.plan_node import plan_node
from services.skill_testing.core.select_skill_node import select_skill_node
from services.skill_testing.core.execute_node import execute_node
from services.skill_testing.core.evaluate_node import evaluate_node
from services.skill_testing.orchestrator import get_compiled_workflow
from shared.schemas import SkillRead

# Custom Mock LLM Client
class MockTestLLMClient:
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.last_call_usage = None
        self.plan_response = '{"plan": ["analyze-stacktrace"]}'
        self.args_response = '{"stacktrace": "NullPointerException at line 10", "file": "LoginService.java"}'
        self.evaluate_response = '{"is_success": true, "analysis": "success"}'
        
    async def call(self, system_prompt: str, user_prompt: str) -> str:
        prompt_tokens = 50
        completion_tokens = 20
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.last_call_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": "mock-model",
            "cost": 0.0001
        }
        
        if "Lead Software Architect" in system_prompt:
            return self.plan_response
        elif "Parameter Extractor" in system_prompt:
            return self.args_response
        elif "Quality Assurance Engineer" in system_prompt:
            return self.evaluate_response
        return "{}"

class VerificationTestSuite(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        # Setup workspace for physical execution tests
        self.workspace_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "test_workspace")
        )
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.skill_client = SkillExecutionClient(workspace_path=self.workspace_dir)
        self.llm_client = MockTestLLMClient()
        
        # Reset registry caches
        semantic_registry._skills_cache = []
        semantic_registry._summary_cache = {}
        semantic_registry._detail_cache = {}
        semantic_registry._embeddings = None
        
    async def asyncTearDown(self):
        # Clean up test workspace
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir, ignore_errors=True)

    # 1. Cache Hit Test
    async def test_cache_hit_get_skills(self):
        # Mock global _SKILL_CACHE in server.py
        from services.skill_testing.server import get_cached_skills, _SKILL_CACHE
        _SKILL_CACHE["tools"] = None  # Reset cache
        
        mock_response = [
            {"name": "analyze-stacktrace", "description": "test", "skill_id": "1"}
        ]
        
        # Patch httpx.AsyncClient.get
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            mock_get.return_value = mock_resp
            
            skills1 = await get_cached_skills()
            self.assertEqual(len(skills1), 1)
            
            skills2 = await get_cached_skills()
            self.assertEqual(len(skills2), 1)
            
            mock_get.assert_called_once_with("http://127.0.0.1:8001/skills/tools", timeout=10.0)

    # 2. Lazy Load Test
    async def test_lazy_load_skill_detail(self):
        mock_skill = SkillRead(
            id="uuid-123",
            name="analyze-stacktrace",
            version="1.0",
            level="atomic",
            category="debug",
            tags=["java"],
            metadata={"description": "Analyzes logs"},
            updated_at=datetime.now(),
            raw_content="instruction detail",
            full_markdown="md"
        )
        semantic_registry.build_index([mock_skill])
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_skill.model_dump()
            mock_get.return_value = mock_resp
            
            # Lazy load 1: detail cache miss -> calls API
            detail1 = await semantic_registry.get_skill_detail("analyze-stacktrace")
            self.assertEqual(detail1.get("raw_content"), "instruction detail")
            mock_get.assert_called_once_with("http://127.0.0.1:8001/skills/uuid-123", timeout=5.0)
            
            # Lazy load 2: detail cache hit -> does NOT call API
            mock_get.reset_mock()
            detail2 = await semantic_registry.get_skill_detail("analyze-stacktrace")
            self.assertEqual(detail2.get("raw_content"), "instruction detail")
            mock_get.assert_not_called()

    # 3. Loop Detection Positive Test
    async def test_loop_detection_positive(self):
        state = AgentState(
            user_context={"code": "...", "stacktrace": "...", "message": "..."},
            plan=["analyze-stacktrace"],
            current_step_idx=0,
            selected_skill="analyze-stacktrace"
        )
        
        mock_llm = MockTestLLMClient()
        mock_llm.evaluate_response = '{"is_success": false, "analysis": "still failing"}'
        
        # Simulating same error 3 times
        state.last_observation = json.dumps({"status": "FAILED", "stderr": "NullPointerException"})
        
        # 1st time
        state.plan = ["analyze-stacktrace"]
        state.current_step_idx = 0
        state = await evaluate_node(state, mock_llm)
        self.assertFalse(state.is_finished)
        self.assertFalse(state.need_replan)
        
        # 2nd time
        state.plan = ["analyze-stacktrace"]
        state.current_step_idx = 0
        state = await evaluate_node(state, mock_llm)
        self.assertFalse(state.is_finished)
        self.assertFalse(state.need_replan)
        
        # 3rd time
        state.plan = ["analyze-stacktrace"]
        state.current_step_idx = 0
        state = await evaluate_node(state, mock_llm)
        self.assertTrue(state.is_finished)
        self.assertTrue(state.need_replan)
        self.assertIn("Infinite loop detected", state.final_answer)

    # 4. Loop Detection Negative Test
    async def test_loop_detection_negative(self):
        state = AgentState(
            user_context={"code": "...", "stacktrace": "...", "message": "..."},
            plan=["analyze-stacktrace"],
            current_step_idx=0,
            selected_skill="analyze-stacktrace"
        )
        
        mock_llm = MockTestLLMClient()
        mock_llm.evaluate_response = '{"is_success": false, "analysis": "failing differently"}'
        
        # Call 1: NullPointerException
        state.last_observation = json.dumps({"status": "FAILED", "stderr": "NullPointerException"})
        state.plan = ["analyze-stacktrace"]
        state.current_step_idx = 0
        state = await evaluate_node(state, mock_llm)
        self.assertFalse(state.is_finished)
        
        # Call 2: ArithmeticException
        state.last_observation = json.dumps({"status": "FAILED", "stderr": "ArithmeticException"})
        state.plan = ["analyze-stacktrace"]
        state.current_step_idx = 0
        state = await evaluate_node(state, mock_llm)
        self.assertFalse(state.is_finished)
        
        # Call 3: ModuleNotFoundError
        state.last_observation = json.dumps({"status": "FAILED", "stderr": "ModuleNotFoundError: requests"})
        state.plan = ["analyze-stacktrace"]
        state.current_step_idx = 0
        state = await evaluate_node(state, mock_llm)
        
        # Loop detector should NOT trigger since the error signatures are different
        self.assertFalse(state.need_replan)
        self.assertFalse(state.is_finished)

    # 5. End-to-End Minimal Flow Test
    async def test_e2e_minimal_flow(self):
        mock_skill = SkillRead(
            id="uuid-123",
            name="analyze-stacktrace",
            version="1.0",
            level="atomic",
            category="debug",
            tags=["java"],
            metadata={
                "description": "Analyzes Java stacktrace to find error line",
                "input": {"stacktrace": {"type": "string"}},
                "output": {"file": {"type": "string"}, "line": {"type": "integer"}}
            },
            updated_at=datetime.now(),
            raw_content="detail text",
            full_markdown="md"
        )
        semantic_registry.build_index([mock_skill])
        
        # Setup real workspace with sample file for the skill to read
        os.makedirs(os.path.join(self.workspace_dir, "src", "main", "java"), exist_ok=True)
        sample_java = os.path.join(self.workspace_dir, "src", "main", "java", "LoginService.java")
        with open(sample_java, "w", encoding="utf-8") as f:
            f.write("public class LoginService {}")
            
        compiled_workflow = get_compiled_workflow(self.llm_client, self.skill_client)
        
        initial_state = {
            "user_context": {
                "code": "public class LoginService {}",
                "stacktrace": "NullPointerException at LoginService:10",
                "message": "Fix NPE"
            },
            "plan": [],
            "current_step_idx": 0,
            "step_count": 0,
            "history": []
        }
        
        final_state = await compiled_workflow.ainvoke(initial_state)
        
        self.assertTrue(final_state.get("is_finished"))
        self.assertIn("SUCCESS", final_state.get("final_answer"))
        self.assertGreater(final_state.get("step_count"), 0)
        self.assertGreater(len(final_state.get("history")), 0)

    # 6. Token Aggregation Test
    async def test_token_aggregation(self):
        state = AgentState(
            user_context={"code": "...", "stacktrace": "...", "message": "..."},
            plan=["analyze-stacktrace"],
            current_step_idx=0,
            selected_skill="analyze-stacktrace"
        )
        
        # Init tokens are 0
        self.assertEqual(state.total_tokens, 0)
        
        # Call plan_node (Mock Test LLM adds 50 + 20 = 70 tokens)
        state = await plan_node(state, self.llm_client)
        self.assertEqual(state.total_tokens, 70)
        
        # Call execute_node (Mock Test LLM adds 70 tokens -> total 140)
        mock_skill = SkillRead(
            id="uuid-123",
            name="analyze-stacktrace",
            version="1.0",
            level="atomic",
            category="debug",
            tags=["java"],
            metadata={"description": "Analyzes logs", "input": {"stacktrace": {"type": "string"}}},
            updated_at=datetime.now(),
            raw_content="detail",
            full_markdown="md"
        )
        semantic_registry.build_index([mock_skill])
        state.selected_skill = "analyze-stacktrace"
        
        state = await execute_node(state, self.llm_client, self.skill_client)
        self.assertEqual(state.total_tokens, 140)

    # 7. Latency Tracking Test
    async def test_latency_tracking(self):
        state = AgentState(
            user_context={"code": "...", "stacktrace": "...", "message": "..."},
            plan=["analyze-stacktrace"],
            current_step_idx=0,
            selected_skill="analyze-stacktrace"
        )
        
        # Setup registry
        mock_skill = SkillRead(
            id="uuid-123",
            name="analyze-stacktrace",
            version="1.0",
            level="atomic",
            category="debug",
            tags=["java"],
            metadata={"description": "Analyzes logs", "input": {"stacktrace": {"type": "string"}}},
            updated_at=datetime.now(),
            raw_content="detail",
            full_markdown="md"
        )
        semantic_registry.build_index([mock_skill])
        
        # Call nodes
        state = await plan_node(state, self.llm_client)
        state = await execute_node(state, self.llm_client, self.skill_client)
        state = await evaluate_node(state, self.llm_client, self.skill_client)
        
        self.assertEqual(len(state.execution_history), 3)
        
        # Verify latency_ms is in all history entries and is integer >= 0
        for entry in state.execution_history:
            self.assertIn("node", entry)
            self.assertIn("latency_ms", entry)
            self.assertIsInstance(entry["latency_ms"], int)
            self.assertGreaterEqual(entry["latency_ms"], 0)

    # 8. Physical Execution Test
    async def test_physical_execution(self):
        # Create a real Python file with correct prints
        py_filename = "test_script.py"
        py_content = """
import sys
print("Output to stdout")
print("Output to stderr", file=sys.stderr)
sys.exit(0)
"""
        py_file_path = self.skill_client.setup_initial_workspace(py_content, py_filename)
        self.assertTrue(os.path.exists(py_file_path))
        
        # Execute skill debug_python_error
        res = await self.skill_client.execute_skill("debug_python_error", {"file": py_filename})
        
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIn("Output to stdout", res.get("stdout"))
        self.assertIn("Output to stderr", res.get("stderr"))
        self.assertEqual(res.get("returncode"), 0)
        
        # Test case with failure (syntax error)
        fail_py_filename = "test_fail.py"
        fail_py_content = "invalid python code syntax"
        self.skill_client.setup_initial_workspace(fail_py_content, fail_py_filename)
        
        res_fail = await self.skill_client.execute_skill("debug_python_error", {"file": fail_py_filename})
        self.assertEqual(res_fail.get("status"), "FAILED")
        self.assertGreater(res_fail.get("returncode"), 0)
        self.assertIn("SyntaxError", res_fail.get("stderr") or res_fail.get("message"))

if __name__ == "__main__":
    unittest.main()
