"""
Unit tests for SWEAgentProCoordinator end-to-end workflow
"""

import unittest
from pathlib import Path
from sweagent_pro.engine.coordinator import SWEAgentProCoordinator


class TestCoordinatorWorkflow(unittest.TestCase):
    def setUp(self):
        self.coordinator = SWEAgentProCoordinator()
        self.repo_path = Path("sample_repos/paginator_offset").resolve()

    def test_full_autonomous_bug_hunt_flow(self):
        issue_text = """
### Title: QuerySet pagination offset skips records

### Expected Behavior:
QuerySet.paginate(page=1, page_size=10) returns items 0-9. Page 2 returns items 10-19.

### Observed Behavior:
QuerySet.paginate(page=2, page_size=10) returns items 20-29.

### Steps to Reproduce:
1. Initialize QuerySet with 30 items
2. Call paginate(page=2, page_size=10)
3. Check first element
"""
        state = self.coordinator.run_hunt(
            raw_issue=issue_text,
            repo_path=str(self.repo_path),
            issue_id="ISSUE-END2END-01",
            test_command="python3 -m unittest test_paginator.py"
        )

        self.assertEqual(state.status, "AWAITING_APPROVAL")
        self.assertIsNotNone(state.current_patch)
        self.assertIsNotNone(state.regression_report)
        self.assertTrue(state.regression_report.safe_to_merge)
        self.assertGreaterEqual(len(state.trace.evidence), 1)
        self.assertGreaterEqual(len(state.hypotheses), 1)
        self.assertGreaterEqual(len(state.audit_trail), 4)


if __name__ == '__main__':
    unittest.main()
