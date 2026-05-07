import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.planner import planner_node


class ReplanningTests(unittest.TestCase):
    def test_replanned_state_creates_fix_code_error_plan(self):
        state = {
            "input": "viet test kiem thu unit test",
            "is_replanned": True,
            "last_error": "missing expected output key: functions",
            "context_memory": {
                "facts": {"last_task_id": "extract-metadata"},
                "task_results": {},
            },
            "metrics": {"total_tokens": 20, "estimated_cost": 0.0004, "total_retries": 3},
        }

        result = planner_node(state)
        tasks = result["plan"]["tasks"]

        self.assertEqual(result["planning_strategy"], "error_recovery_replan")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], "fix_code_error")
        self.assertEqual(tasks[0]["skill_id"], "code-fixer-skill")
        self.assertEqual(tasks[0]["depends_on"], ["extract-metadata"])
        self.assertTrue(result["is_replanned"])


if __name__ == "__main__":
    unittest.main()
