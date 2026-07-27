import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_parser import parse_record

class TestDataParser(unittest.TestCase):
    def test_parse_valid_record(self):
        res = parse_record('{"id": "101", "value": 42.5}')
        self.assertEqual(res["id"], 101)

    def test_parse_missing_id(self):
        res = parse_record('{"value": 10.0}')
        self.assertEqual(res["id"], 0)

if __name__ == "__main__":
    unittest.main()
