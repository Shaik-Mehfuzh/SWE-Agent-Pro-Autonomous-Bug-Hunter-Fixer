"""
Typed data interfaces and schemas for SWE-Agent Pro.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
import json
import time


class FailureClass(str, Enum):
    SUCCESS = "SUCCESS"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    RUNTIME_EXCEPTION = "RUNTIME_EXCEPTION"
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    IMPORT_ERROR = "IMPORT_ERROR"
    REGRESSION = "REGRESSION"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    CONFIRMED = "CONFIRMED"


@dataclass
class IssueSpec:
    id: str
    title: str
    raw_description: str
    expected_behavior: str = ""
    observed_behavior: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    technical_constraints: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileEvidence:
    id: str
    file_path: str
    line_start: int
    line_end: int
    symbol_name: str
    snippet: str
    relevance_rationale: str
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationStep:
    step_number: int
    action: str
    target: str
    rationale: str
    observation: str
    evidence_ids: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvestigationTrace:
    steps: List[InvestigationStep] = field(default_factory=list)
    evidence: List[FileEvidence] = field(default_factory=list)
    unresolved_assumptions: List[str] = field(default_factory=list)
    visited_files: List[str] = field(default_factory=list)
    query_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Hypothesis:
    id: str
    title: str
    description: str
    candidate_files: List[str] = field(default_factory=list)
    code_symbols: List[str] = field(default_factory=list)
    confidence: float = 0.5
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    evidence_ids: List[str] = field(default_factory=list)
    verification_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['verification_status'] = self.verification_status.value
        return d


@dataclass
class PatchFile:
    file_path: str
    original_content: str
    patched_content: str
    diff_content: str
    change_summary: str
    rationale: str
    lines_added: int = 0
    lines_removed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PatchArtifact:
    patch_id: str
    files: List[PatchFile] = field(default_factory=list)
    full_diff: str = ""
    explanation: str = ""
    blast_radius_score: float = 1.0  # 1.0 = minimal, 10.0 = high risk
    touches_unrelated_code: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SandboxResult:
    test_command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time_sec: float
    memory_peak_mb: float
    timed_out: bool
    classification: FailureClass
    isolated_dir: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['classification'] = self.classification.value
        return d


@dataclass
class RepairIteration:
    iteration_number: int
    failure_type: FailureClass
    error_excerpt: str
    patch_applied: Optional[PatchArtifact] = None
    test_result: Optional[SandboxResult] = None
    detected_repeat_pattern: bool = False
    repeat_pattern_detail: str = ""
    resolution_status: str = "PENDING"  # PENDING, REPAIRED, FAILED, EXCEEDED_LIMIT

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['failure_type'] = self.failure_type.value
        return d


@dataclass
class RegressionReport:
    passed_existing_tests: List[str] = field(default_factory=list)
    failed_existing_tests: List[str] = field(default_factory=list)
    bug_reproduction_test_passed: bool = False
    side_effects_detected: List[str] = field(default_factory=list)
    coverage_delta_percent: float = 0.0
    safe_to_merge: bool = False
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditLogEntry:
    id: str
    timestamp: float = field(default_factory=time.time)
    actor: str = "SWE-Agent-Pro"
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    approved: Optional[bool] = None
    reviewer_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkMetric:
    issue_id: str
    agent_type: str  # "swe_agent_pro" vs "baseline_swe_agent"
    resolved: bool
    test_passed: bool
    regression_count: int
    iterations_used: int
    duration_sec: float
    estimated_cost_usd: float
    patch_size_lines: int
    failure_classification: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentRunState:
    run_id: str
    issue: IssueSpec
    repo_snapshot_path: str
    status: str  # INITIALIZING, UNDERSTANDING, INVESTIGATING, HYPOTHESIZING, PATCHING, TESTING, REPAIRING, REGRESSION_CHECK, AWAITING_APPROVAL, COMPLETED, FAILED
    trace: InvestigationTrace = field(default_factory=InvestigationTrace)
    hypotheses: List[Hypothesis] = field(default_factory=list)
    current_patch: Optional[PatchArtifact] = None
    repair_history: List[RepairIteration] = field(default_factory=list)
    regression_report: Optional[RegressionReport] = None
    audit_trail: List[AuditLogEntry] = field(default_factory=list)
    error_message: Optional[str] = None
    human_approved: Optional[bool] = None
    total_cost_usd: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
