"""
Unit tests for Feature 1: Issue Understanding
"""

import unittest
from sweagent_pro.issue_understanding import IssueUnderstandingEngine


class TestIssueUnderstanding(unittest.TestCase):
    def setUp(self):
        self.engine = IssueUnderstandingEngine()

    def test_structured_issue_extraction(self):
        raw = """
### Title: Pagination offset bug in QuerySet.paginate()

### Expected Behavior:
QuerySet.paginate(page=1, page_size=10) should return items 0 through 9, and page=2 should return 10 through 19.

### Observed Behavior:
QuerySet.paginate(page=2, page_size=10) returns items 20 through 29 due to an off-by-one multiplication `(page) * page_size`.

### Steps to Reproduce:
1. Create a queryset with 30 items
2. Call qs.paginate(page=2, page_size=10)
3. Check the returned item IDs

### Constraints:
- Must not break zero-indexed legacy pagination callers
- Must maintain O(1) slicing complexity
        """
        spec = self.engine.parse_issue(raw, issue_id="ISSUE-101")
        
        self.assertEqual(spec.id, "ISSUE-101")
        self.assertIn("QuerySet.paginate", spec.expected_behavior)
        self.assertIn("returns items 20 through 29", spec.observed_behavior)
        self.assertGreaterEqual(len(spec.reproduction_steps), 3)
        self.assertFalse(spec.needs_clarification)
        self.assertGreater(spec.confidence_score, 0.7)
        self.assertTrue(any("zero-indexed" in c for c in spec.technical_constraints))

    def test_missing_info_triggers_clarification(self):
        vague_description = "The app crashes when I click submit."
        spec = self.engine.parse_issue(vague_description, issue_id="ISSUE-102")
        
        self.assertTrue(spec.needs_clarification)
        self.assertIn("reproduction_steps", spec.missing_fields)
        self.assertGreaterEqual(len(spec.clarification_questions), 1)
        self.assertLess(spec.confidence_score, 0.7)


if __name__ == '__main__':
    unittest.main()
