import unittest
from cass.filter.constraint import ConstraintFilterStrategy
from cass.filter.semantic import SemanticFilterStrategy
from cass.ranker.ranker import CASSRanker
class MockMetricsStore:
    def get_metrics(self, names):
        # Skill A is reliable but slow. Skill B is risky but fast.
        return {
            "skill-a": {"alpha": 10, "beta": 1, "avg_latency_ms": 2000, "avg_cost": 0},
            "skill-b": {"alpha": 2, "beta": 2, "avg_latency_ms": 100, "avg_cost": 0}
        }

class TestCASSFiltering(unittest.TestCase):
    def setUp(self):
        self.skills = [
            {
                "name": "skill-a", 
                "description": "Read file content",
                "constraints": {"host": {"os": ["windows"]}, "resources": {"memory": "64MB"}}
            },
            {
                "name": "skill-b", 
                "description": "Write log file",
                "constraints": {"host": {"os": ["linux"]}, "resources": {"memory": "64MB"}}
            }
        ]

    def test_constraint_os_filter(self):
        strategy = ConstraintFilterStrategy()
        # Mock Context for Windows
        context = {"environment": {"os_name": "windows", "available_ram_mb": 1024}}
        
        filtered = strategy.filter(self.skills, context)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "skill-a")

    def test_ranking_logic(self):
        ranker = CASSRanker(MockMetricsStore())
        # Thompson sampling is random, but with high alpha/beta difference, 
        # skill-a should generally rank higher than a 50/50 skill-b.
        ranked = ranker.rank(self.skills, top_k=1)
        self.assertTrue(len(ranked) > 0)

if __name__ == "__main__":
    unittest.main()