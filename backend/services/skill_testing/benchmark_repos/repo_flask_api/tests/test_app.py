import unittest
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import calculate_average, format_user_response

class TestApp(unittest.TestCase):
    def test_calculate_average_empty(self):
        self.assertEqual(calculate_average([]), 0)

    def test_format_user_response_missing_email(self):
        user = {"name": "Alice"}
        self.assertEqual(format_user_response(user), "User Alice <N/A>")

if __name__ == "__main__":
    unittest.main()
