"""
Unit tests for Feature 3: Root-Cause Analysis
"""

import unittest
from sweagent_pro.types import IssueSpec, InvestigationTrace, FileEvidence, VerificationStatus
from sweagent_pro.root_cause_analyzer import RootCauseAnalyzer


class TestRootCauseAnalysis(unittest.TestCase):
    def setUp(self):
        self.analyzer = RootCauseAnalyzer()

    def test_hypotheses_ranking_and_unverified_guard(self):
        issue = IssueSpec(
            id="ISS-301",
            title="QuerySet.paginate off-by-one bug",
            raw_description="Pagination offset skips items when page > 1",
            expected_behavior="Page 1 is offset 0, page 2 is offset 10",
            observed_behavior="Page 2 uses offset 20 instead of 10",
        )
        trace = InvestigationTrace(
            evidence=[
                FileEvidence(
                    id="EV-001",
                    file_path="paginator.py",
                    line_start=8,
                    line_end=12,
                    symbol_name="paginate",
                    snippet="offset = page * page_size\nreturn self.items[offset:offset+page_size]",
                    relevance_rationale="Direct calculation of offset"
                )
            ],
            visited_files=["paginator.py"]
        )

        hypotheses = self.analyzer.generate_hypotheses(issue, trace)

        self.assertGreaterEqual(len(hypotheses), 2)
        # Verify ranked by confidence
        self.assertGreaterEqual(hypotheses[0].confidence, hypotheses[1].confidence)
        # Avoid claiming certainty without verification
        for h in hypotheses:
            self.assertEqual(h.verification_status, VerificationStatus.UNVERIFIED)
            self.assertIn("EV-001", h.evidence_ids)

        # Now empirically verify
        verified = self.analyzer.verify_hypothesis(hypotheses[0], test_passed=True, output_details="All 4 tests passed")
        self.assertEqual(verified.verification_status, VerificationStatus.CONFIRMED)
        self.assertGreaterEqual(verified.confidence, 0.95)


if __name__ == '__main__':
    unittest.main()
