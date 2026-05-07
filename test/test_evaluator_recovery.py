import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.evaluator import evaluator_node, route_after_evaluator


def make_state(output, retry_count=0, error=None):
    task = {
        "id": "extract-metadata",
        "skill_id": "code-parser-skill",
        "expected_outputs": ["functions"],
    }
    return {
        "plan": {"tasks": [task, {"id": "next-task", "expected_outputs": ["code"]}]},
        "scheduler": {"current_step": 0, "next_action": "evaluate"},
        "retry_count": retry_count,
        "context_memory": {
            "task_results": {
                "extract-metadata": {
                    "task_id": "extract-metadata",
                    "output": output,
                    "error": error,
                }
            }
        },
    }


class EvaluatorRecoveryTests(unittest.TestCase):
    def test_empty_output_retries_same_task(self):
        result = evaluator_node(make_state({}))

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["scheduler"]["current_step"], 0)
        self.assertEqual(result["scheduler"]["next_action"], "retry")
        self.assertEqual(route_after_evaluator(result), "retry")

    def test_missing_expected_key_retries_same_task(self):
        result = evaluator_node(make_state({"language": "python"}))

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["last_error"], "missing expected output key: functions")
        self.assertEqual(result["scheduler"]["current_step"], 0)

    def test_empty_expected_key_retries_same_task(self):
        result = evaluator_node(make_state({"language": "unknown", "functions": []}))

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["last_error"], "expected output key is empty: functions")
        self.assertEqual(result["scheduler"]["next_action"], "retry")

    def test_error_text_retries_same_task(self):
        result = evaluator_node(make_state({"functions": "error: parse failed"}))

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["last_error"], "output contains error")
        self.assertEqual(route_after_evaluator(result), "retry")

    def test_execution_error_retries_same_task(self):
        result = evaluator_node(make_state(None, error="tool crashed"))

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["last_error"], "tool crashed")
        self.assertEqual(result["scheduler"]["current_step"], 0)

    def test_valid_expected_output_advances_to_next_task(self):
        result = evaluator_node(make_state({"functions": [{"name": "foo"}]}))

        self.assertEqual(result["retry_count"], 0)
        self.assertEqual(result["scheduler"]["current_step"], 1)
        self.assertEqual(result["scheduler"]["next_action"], "continue")
        self.assertEqual(route_after_evaluator(result), "continue")

    def test_max_retry_continues_instead_of_looping_forever(self):
        state = make_state({"functions": []}, retry_count=2)
        state["is_replanned"] = True
        result = evaluator_node(state)

        self.assertEqual(result["retry_count"], 0)
        self.assertEqual(result["scheduler"]["current_step"], 1)
        self.assertEqual(result["scheduler"]["next_action"], "continue")

    def test_retry_exhaustion_replans_once(self):
        result = evaluator_node(make_state({"functions": []}, retry_count=2))

        self.assertEqual(result["retry_count"], 0)
        self.assertTrue(result["is_replanned"])
        self.assertEqual(result["scheduler"]["current_step"], 0)
        self.assertEqual(result["scheduler"]["next_action"], "replan")
        self.assertEqual(route_after_evaluator(result), "replan")


if __name__ == "__main__":
    unittest.main()
