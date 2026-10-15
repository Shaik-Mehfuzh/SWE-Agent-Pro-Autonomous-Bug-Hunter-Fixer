"""
Unit tests for Feature 6: Bounded Self-Repair
"""

import unittest
import tempfile
from pathlib import Path
from sweagent_pro.types import IssueSpec, Hypothesis, FailureClass
from sweagent_pro.self_repair import BoundedSelfRepairEngine


class TestBoundedSelfRepair(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Code with bug
        code = '''def paginate(items, page=1, page_size=10):
    offset = page * page_size
    return items[offset:offset+page_size]
'''
        (self.repo_path / "paginator.py").write_text(code)

        # Test script that asserts page 1 is offset 0
        test_code = '''import unittest
from paginator import paginate

class TestPagination(unittest.TestCase):
    def test_pages(self):
        data = list(range(30))
        p1 = paginate(data, page=1, page_size=10)
        self.assertEqual(p1, list(range(0, 10)))
        p2 = paginate(data, page=2, page_size=10)
        self.assertEqual(p2, list(range(10, 20)))

if __name__ == '__main__':
    unittest.main()
'''
        (self.repo_path / "test_paginator.py").write_text(test_code)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_repair_loop_fixes_bug_and_verifies(self):
        engine = BoundedSelfRepairEngine(str(self.repo_path), max_retries=3)
        issue = IssueSpec(
            id="ISSUE-601",
            title="Pagination off by one",
            raw_description="offset = page * page_size"
        )
        hyp = Hypothesis(
            id="HYP-001",
            title="Off by one",
            description="offset calculation",
            candidate_files=["paginator.py"]
        )

        success, patch, history = engine.run_repair_loop(
            issue=issue,
            hypothesis=hyp,
            evidence=[],
            verification_test_command="python3 -m unittest test_paginator.py"
        )

        self.assertTrue(success)
        self.assertIsNotNone(patch)
        self.assertEqual(history[0].resolution_status, "REPAIRED")
        self.assertEqual(history[0].test_result.classification, FailureClass.SUCCESS)

    def test_bounded_limit_stops_and_does_not_claim_fix_on_impossible_test(self):
        # Test script that can never pass
        (self.repo_path / "impossible_test.py").write_text('''import unittest
class Impossible(unittest.TestCase):
    def test_never(self):
        self.fail("Permanent impossible assertion")
if __name__ == '__main__':
    unittest.main()
''')
        engine = BoundedSelfRepairEngine(str(self.repo_path), max_retries=2)
        issue = IssueSpec(id="ISS-602", title="Unfixable", raw_description="fail")
        hyp = Hypothesis(id="HYP-002", title="Unfixable", description="", candidate_files=["paginator.py"])

        success, patch, history = engine.run_repair_loop(
            issue=issue,
            hypothesis=hyp,
            evidence=[],
            verification_test_command="python3 -m unittest impossible_test.py"
        )

        # Invariant: Never claim a bug is fixed unless required checks pass!
        self.assertFalse(success)
        self.assertLessEqual(len(history), 2)
        self.assertNotEqual(history[-1].resolution_status, "REPAIRED")


if __name__ == '__main__':
    unittest.main()
