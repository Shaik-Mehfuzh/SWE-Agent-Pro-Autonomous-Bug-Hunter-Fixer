"""
SWE-Agent Pro: Master Agent Coordinator
Orchestrates the complete autonomous bug hunting, investigation, patching,
sandboxed testing, bounded repair, regression verification, and audit trail pipeline.
"""

from __future__ import annotations
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from sweagent_pro.types import (
    IssueSpec,
    AgentRunState,
    AuditLogEntry,
    VerificationStatus,
    FailureClass
)
from sweagent_pro.issue_understanding import IssueUnderstandingEngine
from sweagent_pro.codebase_investigator import CodebaseInvestigator
from sweagent_pro.root_cause_analyzer import RootCauseAnalyzer
from sweagent_pro.patch_generator import PatchGenerator
from sweagent_pro.sandbox_tester import SandboxTester
from sweagent_pro.self_repair import BoundedSelfRepairEngine
from sweagent_pro.regression_protector import RegressionProtector


class SWEAgentProCoordinator:
    def __init__(self, default_max_retries: int = 3):
        self.max_retries = default_max_retries
        self.understanding_engine = IssueUnderstandingEngine()
        self.sandbox_tester = SandboxTester()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.regression_protector = RegressionProtector(self.sandbox_tester)

    def run_hunt(
        self,
        raw_issue: str,
        repo_path: str,
        issue_id: Optional[str] = None,
        title: Optional[str] = None,
        test_command: Optional[str] = None
    ) -> AgentRunState:
        """
        Executes end-to-end autonomous bug hunting and fixing workflow.
        """
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        resolved_issue_id = issue_id or f"ISSUE-{int(time.time()) % 10000}"

        # Phase 1: Issue Understanding
        parsed_issue = self.understanding_engine.parse_issue(
            raw_description=raw_issue,
            issue_id=resolved_issue_id,
            title=title or ""
        )

        state = AgentRunState(
            run_id=run_id,
            issue=parsed_issue,
            repo_snapshot_path=repo_path,
            status="INVESTIGATING",
            start_time=time.time()
        )

        # Audit initial entry
        state.audit_trail.append(AuditLogEntry(
            id=f"AUD-{len(state.audit_trail) + 1:03d}",
            actor="IssueUnderstandingEngine",
            action="PARSED_BUG_REPORT",
            details={
                "issue_id": parsed_issue.id,
                "confidence": parsed_issue.confidence_score,
                "needs_clarification": parsed_issue.needs_clarification,
                "missing_fields": parsed_issue.missing_fields
            }
        ))

        # Check if clarification is strictly required
        if parsed_issue.needs_clarification and parsed_issue.confidence_score < 0.4:
            state.status = "AWAITING_CLARIFICATION"
            state.error_message = "Essential bug details are missing. Clarification requested from user."
            state.end_time = time.time()
            return state

        # Phase 2: Codebase Investigation
        investigator = CodebaseInvestigator(repo_path)
        trace = investigator.investigate(parsed_issue)
        state.trace = trace

        state.audit_trail.append(AuditLogEntry(
            id=f"AUD-{len(state.audit_trail) + 1:03d}",
            actor="CodebaseInvestigator",
            action="INVESTIGATED_CODEBASE",
            details={
                "visited_files": trace.visited_files,
                "evidence_count": len(trace.evidence),
                "assumptions": trace.unresolved_assumptions
            }
        ))

        # Phase 3: Root-Cause Analysis
        hypotheses = self.root_cause_analyzer.generate_hypotheses(parsed_issue, trace)
        state.hypotheses = hypotheses
        primary_hyp = hypotheses[0]

        state.audit_trail.append(AuditLogEntry(
            id=f"AUD-{len(state.audit_trail) + 1:03d}",
            actor="RootCauseAnalyzer",
            action="FORMULATED_HYPOTHESES",
            details={
                "ranked_count": len(hypotheses),
                "top_hypothesis": primary_hyp.title,
                "top_confidence": primary_hyp.confidence,
                "status": primary_hyp.verification_status.value
            }
        ))

        # Determine verification test command
        cmd_to_run = test_command
        if not cmd_to_run:
            # Auto-detect test file
            for f in os.listdir(repo_path):
                if f.startswith("test_") and f.endswith(".py"):
                    cmd_to_run = f"python3 -m unittest {f}"
                    break
            if not cmd_to_run:
                cmd_to_run = "python3 -m unittest discover -s . -p 'test_*.py'"

        # Phase 4 & 5 & 6: Patch Generation, Sandboxed Testing & Bounded Self-Repair
        state.status = "REPAIRING"
        repair_engine = BoundedSelfRepairEngine(
            repo_root=repo_path,
            max_retries=self.max_retries,
            sandbox_tester=self.sandbox_tester
        )

        success, patch, repair_history = repair_engine.run_repair_loop(
            issue=parsed_issue,
            hypothesis=primary_hyp,
            evidence=trace.evidence,
            verification_test_command=cmd_to_run
        )

        state.repair_history = repair_history
        state.current_patch = patch

        # Update hypothesis confirmation status based on test verification
        if success:
            self.root_cause_analyzer.verify_hypothesis(
                primary_hyp,
                test_passed=True,
                output_details=f"Verified through {len(repair_history)} repair iterations."
            )
        else:
            self.root_cause_analyzer.verify_hypothesis(
                primary_hyp,
                test_passed=False,
                output_details="Failed sandboxed verification tests."
            )

        state.audit_trail.append(AuditLogEntry(
            id=f"AUD-{len(state.audit_trail) + 1:03d}",
            actor="BoundedSelfRepairEngine",
            action="COMPLETED_REPAIR_LOOP",
            details={
                "success": success,
                "iterations_used": len(repair_history),
                "patch_id": patch.patch_id if patch else None
            }
        ))

        if not success or not patch:
            state.status = "FAILED"
            state.error_message = "Bounded repair limit reached without passing verification checks."
            state.end_time = time.time()
            return state

        # Phase 7: Regression Protection
        state.status = "REGRESSION_CHECK"
        repro_test = self.regression_protector.generate_reproduction_test(parsed_issue, primary_hyp)
        regression_report = self.regression_protector.evaluate_regression(
            base_repo_dir=repo_path,
            patch=patch,
            existing_test_commands=[cmd_to_run],
            repro_test_filename="test_repro_swe_pro.py",
            repro_test_content=repro_test
        )
        state.regression_report = regression_report

        state.audit_trail.append(AuditLogEntry(
            id=f"AUD-{len(state.audit_trail) + 1:03d}",
            actor="RegressionProtector",
            action="EVALUATED_REGRESSIONS",
            details={
                "safe_to_merge": regression_report.safe_to_merge,
                "passed_existing": len(regression_report.passed_existing_tests),
                "regressions_detected": len(regression_report.failed_existing_tests),
                "reproduction_passed": regression_report.bug_reproduction_test_passed
            }
        ))

        # Calculate estimated cost
        state.total_cost_usd = round(len(repair_history) * 0.0024 + 0.0015, 4)

        # Phase 8: Human Approval Gate
        if regression_report.safe_to_merge:
            state.status = "AWAITING_APPROVAL"
        else:
            state.status = "FAILED"
            state.error_message = f"Patch rejected due to detected regressions: {', '.join(regression_report.failed_existing_tests)}"

        state.end_time = time.time()
        return state
