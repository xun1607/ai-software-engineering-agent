import unittest
import os
from cass.storage.db_manager import SQLiteDBManager, ExecutionRecord
from cass.context.context_manager import CASSContextManager

class TestCASSInfrastructure(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_cass.db"
        self.db = SQLiteDBManager(self.test_db)
        self.context = CASSContextManager()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_database_learning_loop(self):
        # 1. Simulate a success execution
        self.db.update_metrics("test_skill", 150.0, 0.01, True)
        # 2. Simulate a failure execution
        self.db.update_metrics("test_skill", 50.0, 0.0, False)
        
        metrics = self.db.get_metrics(["test_skill"])
        
        # Check Alpha/Beta updates (Initial 1 + 1 success = 2, Initial 1 + 1 fail = 2)
        self.assertEqual(metrics["test_skill"]["alpha"], 2)
        self.assertEqual(metrics["test_skill"]["beta"], 2)
        # Check Average Latency ( (150 + 50) / 2 = 100 )
        self.assertEqual(metrics["test_skill"]["avg_latency_ms"], 100.0)

    def test_context_awareness(self):
        ctx = self.context.get_full_context("sess_123", "Write Python code")
        self.assertIn("os_name", ctx["environment"])
        self.assertIn("available_ram_mb", ctx["environment"])
        
        # Test Blacklist
        self.context.register_session_failure("sess_123", "bad_skill")
        updated_ctx = self.context.get_full_context("sess_123", "retry")
        self.assertIn("bad_skill", updated_ctx["temporary_blacklist"])

if __name__ == "__main__":
    unittest.main()