"""
Feature 6: Bounded Self-Repair
Executes a bounded repair loop when tests fail, analyzes failure feedback,
enforces a hard retry limit, detects repeated failure patterns, and guarantees
that an issue is NEVER claimed as fixed unless all checks pass.
"""

from __future__ import annotations
import os
import shutil
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from sweagent_pro.types import (
    IssueSpec,
    Hypothesis,
    FileEvidence,
    PatchArtifact,
    SandboxResult,
    RepairIteration,
    FailureClass
)
from sweagent_pro.patch_generator import PatchGenerator
from sweagent_pro.sandbox_tester import SandboxTester


class BoundedSelfRepairEngine:
    def __init__(
        self,
        repo_root: str,
        max_retries: int = 3,
        sandbox_tester: Optional[SandboxTester] = None
    ):
        self.repo_root = repo_root
        self.max_retries = max_retries
        self.sandbox_tester = sandbox_tester or SandboxTester()

    def run_repair_loop(
        self,
        issue: IssueSpec,
        hypothesis: Hypothesis,
        evidence: List[FileEvidence],
        verification_test_command: str,
        initial_patch: Optional[PatchArtifact] = None
    ) -> Tuple[bool, Optional[PatchArtifact], List[RepairIteration]]:
        """
        Runs bounded iterations to repair failing test cases without exceeding budget.
        Returns: (success: bool, final_patch: Optional[PatchArtifact], history: List[RepairIteration])
        """
        history: List[RepairIteration] = []
        current_patch = initial_patch
        observed_error_signatures: List[str] = []

        # Isolated workspace for repair attempts
        work_dir = tempfile.mkdtemp(prefix="swe_repair_")

        try:
            shutil.copytree(
                self.repo_root,
                os.path.join(work_dir, "repo"),
                ignore=shutil.ignore_patterns(".git", "node_modules", ".venv", "__pycache__")
            )
            isolated_repo = os.path.join(work_dir, "repo")
            patch_gen = PatchGenerator(isolated_repo)

            for iteration in range(1, self.max_retries + 1):
                # If we don't have a patch yet or this is a retry
                if current_patch is None:
                    repair_ctx = history[-1].error_excerpt if history else None
                    current_patch = patch_gen.generate_minimal_patch(
                        issue=issue,
                        hypothesis=hypothesis,
                        evidence=evidence,
                        repair_context=repair_ctx
                    )

                # Apply current patch to isolated repo
                self._apply_patch_to_dir(isolated_repo, current_patch)

                # Run sandboxed verification test
                test_result = self.sandbox_tester.run_sandboxed(
                    repo_dir=isolated_repo,
                    test_command=verification_test_command
                )

                # Extract error signature
                err_excerpt = self._extract_error_excerpt(test_result.stdout, test_result.stderr)
                repeat_detected = False
                repeat_detail = ""

                # Check for repeated failure patterns
                if err_excerpt and err_excerpt in observed_error_signatures:
                    repeat_detected = True
                    repeat_detail = f"Identical failure pattern detected in iteration {iteration}: '{err_excerpt[:60]}...'"
                elif err_excerpt:
                    observed_error_signatures.append(err_excerpt)

                # Check if test passed
                is_success = (test_result.exit_code == 0 and test_result.classification == FailureClass.SUCCESS)

                iteration_record = RepairIteration(
                    iteration_number=iteration,
                    failure_type=test_result.classification,
                    error_excerpt=err_excerpt,
                    patch_applied=current_patch,
                    test_result=test_result,
                    detected_repeat_pattern=repeat_detected,
                    repeat_pattern_detail=repeat_detail,
                    resolution_status="REPAIRED" if is_success else ("EXCEEDED_LIMIT" if iteration == self.max_retries else "FAILED")
                )
                history.append(iteration_record)

                if is_success:
                    # STRICT RULE: Only claim fixed when verification checks strictly pass
                    return True, current_patch, history

                if repeat_detected and iteration >= 2:
                    # Abort early on repeated failure loop rather than burning tokens/compute
                    iteration_record.resolution_status = "ABORTED_REPEAT_PATTERN"
                    return False, current_patch, history

                # Prepare for next attempt: reset patch and try alternative strategy
                current_patch = None

            # Retries exhausted
            return False, current_patch, history

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _apply_patch_to_dir(self, target_dir: str, patch: PatchArtifact) -> None:
        for pfile in patch.files:
            dest = os.path.join(target_dir, pfile.file_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(pfile.patched_content)

    def _extract_error_excerpt(self, stdout: str, stderr: str) -> str:
        combined = f"{stdout}\n{stderr}"
        lines = [l.strip() for l in combined.split("\n") if l.strip()]
        for line in reversed(lines):
            if any(k in line for k in ["AssertionError", "Error:", "Exception:", "FAILED", "SyntaxError"]):
                return line
        return lines[-1] if lines else "Non-zero exit code"
