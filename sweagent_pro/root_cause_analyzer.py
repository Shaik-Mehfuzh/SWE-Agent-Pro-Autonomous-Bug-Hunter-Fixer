"""
Feature 3: Root-Cause Analysis
Generates ranked root-cause hypotheses, links hypotheses to code and evidence,
and avoids claiming certainty without empirical verification.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from sweagent_pro.types import (
    IssueSpec,
    InvestigationTrace,
    FileEvidence,
    Hypothesis,
    VerificationStatus
)


class RootCauseAnalyzer:
    def __init__(self, model_client: Optional[Any] = None):
        self.model_client = model_client

    def generate_hypotheses(self, issue: IssueSpec, trace: InvestigationTrace) -> List[Hypothesis]:
        """
        Synthesizes investigation evidence and issue specifications into ranked, testable hypotheses.
        """
        hypotheses: List[Hypothesis] = []
        evidence_list = trace.evidence

        if not evidence_list:
            # Fallback hypothesis when no direct symbol match was found
            h_general = Hypothesis(
                id="HYP-001",
                title="Configuration or Entrypoint Dispatch Defect",
                description="The defect stems from unresolved routing, environment configuration, or missing dependency initialization.",
                candidate_files=trace.visited_files[:3],
                confidence=0.35,
                verification_status=VerificationStatus.UNVERIFIED,
                verification_notes="Unverified: Requires execution trace or reproduction script output to localize exact line."
            )
            return [h_general]

        primary_ev = evidence_list[0]
        snippet_text = primary_ev.snippet.lower()
        issue_text = f"{issue.title} {issue.expected_behavior} {issue.observed_behavior}".lower()

        # Check for Common Defect Classes

        # 1. Off-by-one or boundary condition
        if any(term in issue_text or term in snippet_text for term in ["off-by-one", "page", "slice", "index", "offset", "range", "<="]):
            h1 = Hypothesis(
                id=f"HYP-{len(hypotheses) + 1:03d}",
                title="Off-by-One Arithmetic or Slicing Boundary Error",
                description=(
                    f"In `{primary_ev.file_path}` around lines {primary_ev.line_start}-{primary_ev.line_end}, "
                    f"index calculation in `{primary_ev.symbol_name}` likely miscomputes offsets "
                    "(e.g., treating 1-based page indices as 0-based without offset subtraction)."
                ),
                candidate_files=[primary_ev.file_path],
                code_symbols=[primary_ev.symbol_name],
                confidence=0.88,
                verification_status=VerificationStatus.UNVERIFIED,
                evidence_ids=[primary_ev.id],
                verification_notes="Empirical verification pending: Requires executing unit test with boundary values (e.g., page=1 vs page=2)."
            )
            hypotheses.append(h1)

        # 2. None / Null / Missing Key Handling
        if any(term in issue_text or term in snippet_text for term in ["none", "null", "keyerror", "attributeerror", "typeerror", "empty", "default"]):
            h_null = Hypothesis(
                id=f"HYP-{len(hypotheses) + 1:03d}",
                title="Unchecked Null / NoneType or Missing Key Access",
                description=(
                    f"Function `{primary_ev.symbol_name}` fails to guard against None or uninitialized attributes "
                    f"in `{primary_ev.file_path}`, resulting in runtime failure on unexpected caller inputs."
                ),
                candidate_files=[primary_ev.file_path],
                code_symbols=[primary_ev.symbol_name],
                confidence=0.78,
                verification_status=VerificationStatus.UNVERIFIED,
                evidence_ids=[primary_ev.id],
                verification_notes="Requires running isolated test passing None or empty payload."
            )
            hypotheses.append(h_null)

        # 3. Parameter Validation or Signature Discrepancy
        h_param = Hypothesis(
            id=f"HYP-{len(hypotheses) + 1:03d}",
            title="Caller Contract or Type Coercion Discrepancy",
            description=(
                f"Defect is caused by invalid parameter sanitization or implicit type coercion "
                f"passed into `{primary_ev.symbol_name}`."
            ),
            candidate_files=[primary_ev.file_path],
            code_symbols=[primary_ev.symbol_name],
            confidence=0.55,
            verification_status=VerificationStatus.UNVERIFIED,
            evidence_ids=[primary_ev.id],
            verification_notes="Requires inspecting call sites and verifying argument types across caller stack."
        )
        hypotheses.append(h_param)

        # 4. Secondary hypothesis for additional evidence files if available
        if len(evidence_list) > 1:
            sec_ev = evidence_list[1]
            h_sec = Hypothesis(
                id=f"HYP-{len(hypotheses) + 1:03d}",
                title=f"Secondary Component Failure in {sec_ev.symbol_name}",
                description=f"Side-effect or failure propagation originating in `{sec_ev.file_path}` ({sec_ev.symbol_name}).",
                candidate_files=[sec_ev.file_path],
                code_symbols=[sec_ev.symbol_name],
                confidence=0.45,
                verification_status=VerificationStatus.UNVERIFIED,
                evidence_ids=[sec_ev.id],
                verification_notes="Secondary candidate: Verify primary hypothesis first before investigating secondary dependencies."
            )
            hypotheses.append(h_sec)

        # Sort hypotheses by confidence descending
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        return hypotheses

    def verify_hypothesis(self, hypothesis: Hypothesis, test_passed: bool, output_details: str = "") -> Hypothesis:
        """
        Updates hypothesis status based on empirical sandbox verification results.
        """
        if test_passed:
            hypothesis.verification_status = VerificationStatus.CONFIRMED
            hypothesis.verification_notes = f"CONFIRMED by successful sandbox verification test run. {output_details}".strip()
            hypothesis.confidence = 0.98
        else:
            hypothesis.verification_status = VerificationStatus.SUPPORTED if "assertion" in output_details.lower() else VerificationStatus.REFUTED
            hypothesis.verification_notes = f"Tested with sandbox run. Details: {output_details}".strip()
        return hypothesis
