"""
Feature 2: Codebase Investigation
Searches relevant files, symbols, builds structured investigation trace,
explains file relevance, and tracks evidence and unresolved assumptions.
"""

from __future__ import annotations
import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from sweagent_pro.types import (
    IssueSpec,
    InvestigationTrace,
    InvestigationStep,
    FileEvidence
)


class CodebaseInvestigator:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root).resolve()
        self.ignored_dirs = {
            ".git", "__pycache__", "node_modules", "dist", "build", 
            ".pytest_cache", ".venv", "venv", ".egg-info"
        }
        self.supported_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".md"}

    def investigate(self, issue: IssueSpec, max_steps: int = 8) -> InvestigationTrace:
        """
        Executes a systematic, hypothesis-driven codebase investigation.
        """
        trace = InvestigationTrace()
        
        # Step 1: Extract keywords and candidate symbols from issue
        keywords = self._extract_search_keywords(issue)
        step1 = InvestigationStep(
            step_number=1,
            action="KEYWORD_EXTRACTION",
            target=", ".join(keywords[:5]),
            rationale="Identify primary search terms and symbols from issue title, observed behavior, and steps.",
            observation=f"Extracted {len(keywords)} candidate tokens: {keywords[:6]}"
        )
        trace.steps.append(step1)
        trace.query_log.extend(keywords[:6])

        # Step 2: Search for matching filenames
        matched_files: List[Path] = []
        for kw in keywords[:4]:
            found = self.find_files_by_pattern(kw)
            for f in found:
                if f not in matched_files:
                    matched_files.append(f)

        step2 = InvestigationStep(
            step_number=2,
            action="FILE_DISCOVERY",
            target="Repository file tree",
            rationale="Locate files whose path or name relates to the issue subject.",
            observation=f"Discovered {len(matched_files)} candidate source files: {[f.name for f in matched_files[:5]]}"
        )
        trace.steps.append(step2)

        # Step 3: Symbol and content search across codebase
        evidence_found: List[FileEvidence] = []
        scanned_files: Set[str] = set()

        for kw in keywords[:6]:
            results = self.search_symbol_or_text(kw)
            for r in results:
                rel_path = str(r['file_path'].relative_to(self.repo_root))
                scanned_files.add(rel_path)
                
                # Check if already captured
                if not any(e.file_path == rel_path and e.line_start == r['line_start'] for e in evidence_found):
                    evidence_id = f"EV-{len(evidence_found) + 1:03d}"
                    ev = FileEvidence(
                        id=evidence_id,
                        file_path=rel_path,
                        line_start=r['line_start'],
                        line_end=r['line_end'],
                        symbol_name=r.get('symbol_name', kw),
                        snippet=r['snippet'],
                        relevance_rationale=r['rationale'],
                        confidence=r.get('confidence', 0.8)
                    )
                    evidence_found.append(ev)

        trace.evidence = evidence_found
        trace.visited_files = list(scanned_files)

        step3 = InvestigationStep(
            step_number=3,
            action="SYMBOL_ANALYSIS",
            target=f"{len(scanned_files)} files scanned",
            rationale="Inspect call sites, method definitions, and error sources.",
            observation=f"Collected {len(evidence_found)} pieces of code evidence.",
            evidence_ids=[e.id for e in evidence_found]
        )
        trace.steps.append(step3)

        # Step 4: Formulate unresolved assumptions
        trace.unresolved_assumptions = self._generate_assumptions(issue, evidence_found)
        step4 = InvestigationStep(
            step_number=4,
            action="ASSUMPTION_AUDIT",
            target="Investigation boundaries",
            rationale="Explicitly list working assumptions that require test verification.",
            observation=f"Identified {len(trace.unresolved_assumptions)} critical assumptions."
        )
        trace.steps.append(step4)

        return trace

    def find_files_by_pattern(self, pattern: str) -> List[Path]:
        matches: List[Path] = []
        pat_lower = pattern.lower()
        if not self.repo_root.exists():
            return matches

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            for file in files:
                p = Path(root) / file
                if p.suffix in self.supported_extensions:
                    if pat_lower in file.lower() or pat_lower in str(p.relative_to(self.repo_root)).lower():
                        matches.append(p)
        return matches

    def search_symbol_or_text(self, term: str, max_results: int = 5) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not term or len(term) < 2 or not self.repo_root.exists():
            return results

        pattern = re.compile(re.escape(term), re.IGNORECASE)

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            for file in files:
                p = Path(root) / file
                if p.suffix not in self.supported_extensions:
                    continue

                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for idx, line in enumerate(lines):
                        if pattern.search(line):
                            line_no = idx + 1
                            start = max(0, idx - 2)
                            end = min(len(lines), idx + 3)
                            snippet = "".join(lines[start:end])
                            
                            # Deduce symbol or enclosing function
                            symbol = self._deduce_enclosing_symbol(lines, idx) or term
                            rationale = f"Matched search query '{term}' in {p.name}:{line_no} inside '{symbol}'"
                            
                            confidence = 0.85 if term.lower() in line.lower() else 0.70
                            if "def " in line or "class " in line:
                                confidence = 0.95

                            results.append({
                                "file_path": p,
                                "line_start": start + 1,
                                "line_end": end,
                                "symbol_name": symbol,
                                "snippet": snippet.strip(),
                                "rationale": rationale,
                                "confidence": confidence
                            })
                            if len(results) >= max_results:
                                return results
                except Exception:
                    continue

        return results

    def _deduce_enclosing_symbol(self, lines: List[str], target_idx: int) -> Optional[str]:
        for i in range(target_idx, -1, -1):
            line = lines[i].strip()
            if line.startswith("def ") or line.startswith("class "):
                parts = line.split("(")
                return parts[0].replace("def ", "").replace("class ", "").strip()
            if "function " in line or "const " in line:
                m = re.search(r"(?:function|const|let|var)\s+([a-zA-Z0-9_]+)", line)
                if m:
                    return m.group(1)
        return None

    def _extract_search_keywords(self, issue: IssueSpec) -> List[str]:
        text = f"{issue.title} {issue.expected_behavior} {issue.observed_behavior} {' '.join(issue.reproduction_steps)}"
        # Extract camelCase, snake_case, identifiers with dots like QuerySet.paginate
        identifiers = re.findall(r"\b[A-Za-z_][A-Za-z0-9_\.]+\b", text)
        stopwords = {
            "the", "and", "for", "with", "from", "should", "return", "returns",
            "actual", "expected", "observed", "issue", "bug", "fails", "error",
            "behavior", "call", "step", "steps", "reproduce", "test", "when"
        }
        filtered: List[str] = []
        for ident in identifiers:
            low = ident.lower()
            if low not in stopwords and len(ident) > 2:
                if ident not in filtered:
                    filtered.append(ident)
        return filtered

    def _generate_assumptions(self, issue: IssueSpec, evidence: List[FileEvidence]) -> List[str]:
        assumptions: List[str] = []
        if evidence:
            primary_file = evidence[0].file_path
            assumptions.append(f"Assuming root cause is localized within `{primary_file}` and its direct call hierarchy.")
        else:
            assumptions.append("Assuming defect is triggered in runtime routing or configuration.")

        if any("page" in issue.raw_description.lower() for _ in [1]):
            assumptions.append("Assuming pagination indices follow standard 1-based indexing for user-facing API contracts.")
        
        assumptions.append("Assuming existing unit tests cover normal baseline behavior without false positives.")
        assumptions.append("Assuming external environment constraints (memory/network) do not cause the observed failure.")
        return assumptions
