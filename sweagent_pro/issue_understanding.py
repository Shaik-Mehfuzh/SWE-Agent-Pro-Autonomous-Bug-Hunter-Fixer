"""
Feature 1: Issue Understanding
Extracts expected behavior, observed behavior, constraints, and reproduction steps.
Detects missing information and generates clarification questions.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from sweagent_pro.types import IssueSpec


class IssueUnderstandingEngine:
    def __init__(self, model_client: Optional[Any] = None):
        self.model_client = model_client

    def parse_issue(self, raw_description: str, issue_id: str = "ISSUE-001", title: str = "") -> IssueSpec:
        """
        Parses a bug description into a structured IssueSpec.
        """
        text = raw_description.strip()
        lines = [line.strip() for line in text.split("\n")]
        
        if not title and lines:
            # Use first non-empty line as title if title not provided
            first_line = lines[0].lstrip("#").strip()
            title = first_line[:80] if len(first_line) > 80 else first_line

        expected = self._extract_expected_behavior(text)
        observed = self._extract_observed_behavior(text)
        steps = self._extract_reproduction_steps(text)
        constraints = self._extract_constraints(text)
        
        missing_fields: List[str] = []
        clarification_questions: List[str] = []

        if not expected:
            missing_fields.append("expected_behavior")
            clarification_questions.append("What is the exact expected behavior or return value when this function runs?")
        
        if not observed:
            missing_fields.append("observed_behavior")
            clarification_questions.append("What specific error, exception, or incorrect output was observed?")

        if not steps:
            missing_fields.append("reproduction_steps")
            clarification_questions.append("Could you provide minimal reproduction code or steps to reproduce the issue?")

        needs_clarification = len(missing_fields) >= 2 or (not steps and not observed)
        
        # Calculate confidence score
        confidence = 1.0 - (len(missing_fields) * 0.25)
        if len(text) < 30:
            confidence = max(0.1, confidence - 0.4)
            needs_clarification = True
            clarification_questions.append("The issue description is very brief. Can you supply more context or relevant stack traces?")
        
        confidence = max(0.1, min(1.0, confidence))

        return IssueSpec(
            id=issue_id,
            title=title or "Reported Software Bug",
            raw_description=raw_description,
            expected_behavior=expected,
            observed_behavior=observed,
            reproduction_steps=steps,
            technical_constraints=constraints,
            missing_fields=missing_fields,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions,
            confidence_score=round(confidence, 2)
        )

    def _extract_expected_behavior(self, text: str) -> str:
        # Match explicit headers or semantic keywords
        patterns = [
            r"(?:###\s*)?(?:Expected Behavior|Expected|Should be|Expected outcome)[:\s]+(.*?)(?=\n\n|\n###|\n[A-Z][a-zA-Z\s]+:|$)",
            r"(?:The system should|Expected to|Expected result:)\s*(.*?)(?=\n\n|\n[A-Z][a-zA-Z\s]+:|$)",
            r"(?:expected\s+to\s+return\s+)(.*?)(?=\n|\.|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                if val:
                    return val

        # Fallback keyword scan
        for line in text.split("\n"):
            line_clean = line.strip()
            if any(line_clean.lower().startswith(p) for p in ["expected:", "should return", "should be:", "must return"]):
                return line_clean.split(":", 1)[-1].strip() or line_clean
        return ""

    def _extract_observed_behavior(self, text: str) -> str:
        patterns = [
            r"(?:###\s*)?(?:Observed Behavior|Actual Behavior|Actual|Current Behavior|Error|Traceback)[:\s]+(.*?)(?=\n\n|\n###|\n[A-Z][a-zA-Z\s]+:|$)",
            r"(?:Instead it|Instead of|Currently fails with|Throws|Error message:)\s*(.*?)(?=\n\n|\n[A-Z][a-zA-Z\s]+:|$)",
            r"(Traceback \(most recent call last\):[\s\S]+?(?=\n\n|$))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1).strip()
                if val:
                    return val

        # Fallback keyword scan
        for line in text.split("\n"):
            line_clean = line.strip()
            if any(line_clean.lower().startswith(p) for p in ["actual:", "observed:", "fails with:", "raises:"]):
                return line_clean.split(":", 1)[-1].strip() or line_clean
            if "error:" in line_clean.lower() or "exception:" in line_clean.lower():
                return line_clean
        return ""

    def _extract_reproduction_steps(self, text: str) -> List[str]:
        steps: List[str] = []
        # Check for Steps to reproduce section
        repro_section = re.search(
            r"(?:###\s*)?(?:Steps to Reproduce|Reproduction Steps|How to Reproduce)[:\s]+(.*?)(?=\n\n\n|\n###|\nExpected|\nObserved|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        target_text = repro_section.group(1) if repro_section else text

        # Check for numbered steps (1. do this, 2. do that)
        numbered_steps = re.findall(r"(?:^|\n)\s*(?:\d+[\.\)]|\-|\*)\s+([^\n]+)", target_text)
        if numbered_steps and len(numbered_steps) >= 1:
            for s in numbered_steps:
                clean_s = s.strip()
                if clean_s and not any(clean_s.lower().startswith(x) for x in ["expected", "actual", "note"]):
                    steps.append(clean_s)
        
        # Check for code block reproduction snippets
        code_blocks = re.findall(r"```(?:python|bash|sh)?\n(.*?)```", text, re.DOTALL)
        if code_blocks and not steps:
            for block in code_blocks:
                for line in block.strip().split("\n"):
                    if line.strip() and not line.strip().startswith("#"):
                        steps.append(line.strip())

        return steps[:10]  # Cap at 10 steps

    def _extract_constraints(self, text: str) -> List[str]:
        constraints: List[str] = [
            "Must preserve existing public API signatures",
            "Must not degrade execution performance"
        ]
        
        # Look for explicit constraint keywords
        constraint_section = re.search(
            r"(?:###\s*)?(?:Constraints|Technical Constraints|Requirements)[:\s]+(.*?)(?=\n\n|\n###|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if constraint_section:
            items = re.findall(r"(?:^|\n)\s*(?:\d+[\.\)]|\-|\*)\s+([^\n]+)", constraint_section.group(1))
            for item in items:
                if item.strip():
                    constraints.append(item.strip())

        if "backward compatibility" in text.lower() or "backwards compatible" in text.lower():
            constraints.append("Must maintain backward compatibility with older inputs")
        if "thread-safe" in text.lower() or "concurrency" in text.lower():
            constraints.append("Must be thread-safe under concurrent operations")
        if "no dependencies" in text.lower() or "zero dependency" in text.lower():
            constraints.append("Must not introduce external dependencies")
            
        # Deduplicate
        return list(dict.fromkeys(constraints))
