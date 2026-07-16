import unittest
import os
from cass.storage.db_manager import SQLiteDBManager
from cass.observer.performance_observer import PerformanceObserver
from cass.adapter.unified_adapter import UnifiedSkillAdapter
from cass.proxy.skill_proxy import CASSSkillProxy

# A mock skill to test
def mock_calculate_sum(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

class TestCASSStandardization(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_stage2.db"
        self.db_manager = SQLiteDBManager(self.db_path)
        self.observer = PerformanceObserver(self.db_manager, self.db_manager)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_full_adaptation_and_execution_loop(self):
        # 1. Test Adapter (Standardization)
        profile = UnifiedSkillAdapter.python_to_cass_profile(mock_calculate_sum)
        self.assertEqual(profile["name"], "mock-calculate-sum")
        self.assertEqual(profile["input"]["properties"]["a"]["type"], "integer")
        self.assertEqual(profile["constraints"]["resources"]["timeout"], 60)

        # 2. Test Proxy (Instrumentation)
        proxy = CASSSkillProxy(mock_calculate_sum, "session-001", self.observer)
        
        # Execute twice successfully
        proxy(a=10, b=20)
        proxy(a=5, b=5)

        # 3. Verify Database Updates
        metrics = self.db_manager.get_metrics(["mock-calculate-sum"])
        reputation = metrics["mock-calculate-sum"]
        
        # alpha should be 1 (initial) + 2 (successes) = 3
        self.assertEqual(reputation["alpha"], 3)
        self.assertEqual(reputation["total_runs"], 2)
        self.assertGreater(reputation["avg_latency_ms"], 0)

if __name__ == "__main__":
    unittest.main()