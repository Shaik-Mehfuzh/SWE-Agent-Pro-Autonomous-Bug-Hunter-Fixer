"""
Unit tests for Feature 5: Sandboxed Testing
"""

import unittest
import tempfile
from pathlib import Path
from sweagent_pro.types import FailureClass
from sweagent_pro.sandbox_tester import SandboxTester


class TestSandboxTesting(unittest.TestCase):
    def setUp(self):
        self.tester = SandboxTester(default_timeout_sec=3.0)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Create a passing test and a failing test
        test_content = '''import unittest

class DummyTests(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(1 + 1, 2)

    def test_fail(self):
        self.assertEqual(2 + 2, 5)

if __name__ == '__main__':
    unittest.main()
'''
        (self.repo_path / "test_sample.py").write_text(test_content)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sandboxed_passing_run(self):
        cmd = "python3 test_sample.py DummyTests.test_pass"
        res = self.tester.run_sandboxed(str(self.repo_path), cmd)
        self.assertEqual(res.exit_code, 0)
        self.assertEqual(res.classification, FailureClass.SUCCESS)
        self.assertFalse(res.timed_out)

    def test_sandboxed_assertion_failure_classification(self):
        cmd = "python3 test_sample.py DummyTests.test_fail"
        res = self.tester.run_sandboxed(str(self.repo_path), cmd)
        self.assertNotEqual(res.exit_code, 0)
        self.assertEqual(res.classification, FailureClass.ASSERTION_FAILURE)

    def test_security_whitelist_blocks_forbidden_command(self):
        cmd = "rm -rf /tmp/some_dir"
        res = self.tester.run_sandboxed(str(self.repo_path), cmd)
        self.assertEqual(res.classification, FailureClass.PERMISSION_DENIED)
        self.assertIn("SECURITY VIOLATION", res.stderr)


if __name__ == '__main__':
    unittest.main()
