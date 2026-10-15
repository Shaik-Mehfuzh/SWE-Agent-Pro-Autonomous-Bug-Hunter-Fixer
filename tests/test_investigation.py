"""
Unit tests for Feature 2: Codebase Investigation
"""

import unittest
import tempfile
import os
from pathlib import Path
from sweagent_pro.types import IssueSpec
from sweagent_pro.codebase_investigator import CodebaseInvestigator


class TestCodebaseInvestigation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Create sample repo files
        src_dir = self.repo_path / "sample_module"
        src_dir.mkdir(parents=True)
        
        paginator_code = '''
class QuerySet:
    def __init__(self, items):
        self.items = items

    def paginate(self, page=1, page_size=10):
        """Paginate items."""
        # BUG: off-by-one multiplication
        offset = page * page_size
        return self.items[offset : offset + page_size]
'''
        (src_dir / "paginator.py").write_text(paginator_code)
        (src_dir / "__init__.py").write_text("# init")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_investigator_finds_symbols_and_builds_trace(self):
        issue = IssueSpec(
            id="ISSUE-201",
            title="Fix QuerySet.paginate offset error",
            raw_description="QuerySet.paginate multiplies page by page_size directly without subtracting 1.",
            expected_behavior="QuerySet.paginate should return 1st page at offset 0",
            observed_behavior="Page 2 skips items",
            reproduction_steps=["QuerySet(range(20)).paginate(page=2, page_size=10)"]
        )

        investigator = CodebaseInvestigator(str(self.repo_path))
        trace = investigator.investigate(issue)

        self.assertGreater(len(trace.steps), 2)
        self.assertTrue(any("paginator.py" in str(f) for f in trace.visited_files))
        self.assertGreater(len(trace.evidence), 0)
        self.assertIn("paginate", trace.evidence[0].symbol_name)
        self.assertGreater(len(trace.unresolved_assumptions), 1)
        self.assertTrue(trace.steps[0].rationale != "")


if __name__ == '__main__':
    unittest.main()
