"""
Unit tests for Feature 9: Evaluation Benchmark
"""

import unittest
from sweagent_pro.benchmark import SWEBenchmarkSuite


class TestBenchmark(unittest.TestCase):
    def setUp(self):
        self.suite = SWEBenchmarkSuite()

    def test_benchmark_runs_and_measures_real_metrics(self):
        results = self.suite.run_benchmark(max_issues=2)
        
        self.assertIn("summary", results)
        self.assertIn("pro", results["summary"])
        self.assertIn("baseline", results["summary"])
        
        pro_summary = results["summary"]["pro"]
        self.assertGreaterEqual(pro_summary["resolution_rate_percent"], 50.0)
        self.assertGreaterEqual(pro_summary["test_pass_rate_percent"], 50.0)
        self.assertEqual(len(results["limitations"]), 3)
        self.assertEqual(len(results["pro_details"]), 2)


if __name__ == '__main__':
    unittest.main()
