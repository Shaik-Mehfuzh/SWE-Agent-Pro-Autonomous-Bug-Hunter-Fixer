"""
Unit tests for Feature 7: Regression Protection
"""

import unittest
import tempfile
from pathlib import Path
from sweagent_pro.types import IssueSpec, Hypothesis, PatchFile, PatchArtifact
from sweagent_pro.regression_protector import RegressionProtector


class TestRegressionProtection(unittest.TestCase):
    def setUp(self):
        self.protector = RegressionProtector()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Baseline module
        paginator_code = '''def paginate(items, page=1, page_size=10):
    offset = page * page_size
    return items[offset:offset+page_size]

def get_total_count(items):
    return len(items)
'''
        (self.repo_path / "paginator.py").write_text(paginator_code)

        # Existing test file that tests get_total_count
        test_existing = '''import unittest
from paginator import get_total_count

class TestExisting(unittest.TestCase):
    def test_total_count(self):
        self.assertEqual(get_total_count([1, 2, 3]), 3)

if __name__ == '__main__':
    unittest.main()
'''
        (self.repo_path / "test_existing.py").write_text(test_existing)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_safe_patch_passes_regression_check(self):
        # A good patch that fixes paginate without touching get_total_count
        patched_code = '''def paginate(items, page=1, page_size=10):
    offset = max(0, page - 1) * page_size
    return items[offset:offset+page_size]

def get_total_count(items):
    return len(items)
'''
        patch = PatchArtifact(
            patch_id="PATCH-001",
            files=[
                PatchFile(
                    file_path="paginator.py",
                    original_content=(self.repo_path / "paginator.py").read_text(),
                    patched_content=patched_code,
                    diff_content="-    offset = page * page_size\n+    offset = max(0, page - 1) * page_size",
                    change_summary="Fixed 1-based offset",
                    rationale="Fix offset bug"
                )
            ]
        )

        report = self.protector.evaluate_regression(
            base_repo_dir=str(self.repo_path),
            patch=patch,
            existing_test_commands=["python3 -m unittest test_existing.py"]
        )

        self.assertTrue(report.safe_to_merge)
        self.assertEqual(len(report.passed_existing_tests), 1)
        self.assertEqual(len(report.failed_existing_tests), 0)

    def test_regressive_patch_is_caught_and_rejected(self):
        # A bad patch that deletes or breaks get_total_count
        bad_patched_code = '''def paginate(items, page=1, page_size=10):
    return []

# BROKE get_total_count
def get_total_count(items):
    raise RuntimeError("Broken by regression!")
'''
        patch = PatchArtifact(
            patch_id="PATCH-002",
            files=[
                PatchFile(
                    file_path="paginator.py",
                    original_content=(self.repo_path / "paginator.py").read_text(),
                    patched_content=bad_patched_code,
                    diff_content="broken",
                    change_summary="Bad patch",
                    rationale="Bad patch"
                )
            ]
        )

        report = self.protector.evaluate_regression(
            base_repo_dir=str(self.repo_path),
            patch=patch,
            existing_test_commands=["python3 -m unittest test_existing.py"]
        )

        self.assertFalse(report.safe_to_merge)
        self.assertTrue(any("REGRESSION" in err for err in report.failed_existing_tests))


if __name__ == '__main__':
    unittest.main()
