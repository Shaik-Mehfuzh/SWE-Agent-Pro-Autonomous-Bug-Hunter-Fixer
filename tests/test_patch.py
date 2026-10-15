"""
Unit tests for Feature 4: Patch Generation
"""

import unittest
import tempfile
from pathlib import Path
from sweagent_pro.types import IssueSpec, Hypothesis, FileEvidence
from sweagent_pro.patch_generator import PatchGenerator


class TestPatchGeneration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        code = '''def paginate(items, page=1, page_size=10):
    offset = page * page_size
    return items[offset:offset+page_size]
'''
        (self.repo_path / "paginator.py").write_text(code)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generates_minimal_unified_diff(self):
        generator = PatchGenerator(str(self.repo_path))
        issue = IssueSpec(
            id="ISSUE-401",
            title="Offset error in paginator",
            raw_description="offset = page * page_size is off by one"
        )
        hyp = Hypothesis(
            id="HYP-001",
            title="Off-by-one in paginator.py",
            description="offset calculation",
            candidate_files=["paginator.py"]
        )

        artifact = generator.generate_minimal_patch(issue, hyp, [])

        self.assertEqual(len(artifact.files), 1)
        self.assertIn("-    offset = page * page_size", artifact.full_diff)
        self.assertIn("+    offset = max(0, page - 1) * page_size", artifact.full_diff)
        self.assertLessEqual(artifact.blast_radius_score, 2.5)
        self.assertFalse(artifact.touches_unrelated_code)
        self.assertTrue(artifact.files[0].rationale != "")


if __name__ == '__main__':
    unittest.main()
