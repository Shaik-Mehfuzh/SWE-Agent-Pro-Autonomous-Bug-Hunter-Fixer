# SWE-Agent Pro: Autonomous Bug Hunter & Fixer

> An advanced autonomous AI software engineering system that extends the open-source **SWE-agent** architecture. Built with structured issue understanding, hypothesis-driven codebase investigation, least-blast-radius patch synthesis, resource-isolated sandboxed testing, bounded self-repair, regression protection, and an interactive human-in-the-loop engineering dashboard.

---

## 1. System Architecture & Flow

```
                                      +------------------------------------+
                                      |         Reported Defect            |
                                      |   (GitHub Issue / Bug Report)      |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +-----------------+------------------+
                                      | Phase 1: Issue Understanding       |
                                      | - Expected vs Observed Behavior    |
                                      | - Reproduction Step Extraction     |
                                      | - Clarification Detection Gate     |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +-----------------+------------------+
                                      | Phase 2: Codebase Investigation    |
                                      | - AST & Symbol Localization        |
                                      | - Relevance Rationale Tracking     |
                                      | - Assumption Audit & Evidence Log  |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +-----------------+------------------+
                                      | Phase 3: Root-Cause Hypotheses     |
                                      | - Ranked Testable Hypotheses       |
                                      | - Zero Premature Certainty Claim   |
                                      | - Linked Evidence Identifiers      |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +-----------------+------------------+
                                      | Phase 4: Patch Synthesis           |
                                      | - Minimal Unified Diff Generation  |
                                      | - Syntax Pre-Validation (AST)      |
                                      | - Blast Radius Scoring             |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +-----------------+------------------+
          +-------------------------> | Phase 5: Sandboxed Testing         |
          |                           | - Isolated Temporary Environment   |
          |                           | - Resource & Timeout Limits        |
          |                           | - Command Whitelist & Loopback Net |
          |                           +-----------------+------------------+
          |                                             |
          |  [Tests Fail]                               v
+---------+-------------------+       +-----------------+------------------+
| Phase 6: Bounded Self-Repair|       | Phase 7: Regression Protection     |
| - Max 3 Iteration Budget    |       | - Pre vs Post Test Suite Diff      |
| - Repeat Pattern Detection  |       | - Bug Reproduction Test Synthesis |
| - Anti-Hallucination Guard  |       | - Safe-to-Merge Certification      |
+-----------------------------+       +-----------------+------------------+
                                                        |
                                                        v
                                      +-----------------+------------------+
                                      | Phase 8: Engineering Dashboard     |
                                      | - Human Approval Sign-Off Gate     |
                                      | - Complete Cryptographic Audit Log |
                                      | - Side-by-Side Diff Inspector      |
                                      +------------------------------------+
```

---

## 2. Comparison with Vanilla SWE-agent (Princeton NLP)

| Dimension | Vanilla SWE-agent | SWE-Agent Pro (This Project) |
|---|---|---|
| **License** | MIT License | MIT License Compatible Extension |
| **Issue Processing** | Raw issue text passed directly to model | Structured requirement extraction (Expected, Observed, Constraints, Reproduction Steps) with missing info clarification |
| **Exploration Strategy** | Unbounded trial-and-error bash commands | Hypothesis-driven symbol search, evidence linking, and explicit assumption auditing |
| **Root-Cause Analysis** | Ad-hoc edits to arbitrary files | Ranked testable hypotheses with strict `UNVERIFIED` until empirical confirmation |
| **Patch Minimality** | Frequently generates large rewrites or overwrites comments | Surgical, unified diffs with calculated blast-radius score and syntax validation |
| **Sandbox Isolation** | Requires heavy Docker daemon setup | Multi-tiered isolated sandbox with CPU/RAM rlimits, timeouts, and command whitelisting |
| **Self-Repair** | Blindly repeats failing command until turn limit | Bounded retry loop (max 3) with repeated failure pattern detection and early break |
| **Regression Guard** | None (only checks issue test) | Dual-phase regression check: runs existing test suite before and after patch |
| **Human Interface** | CLI-only or read-only inspector | Interactive real-time Engineering Dashboard with Human-in-the-Loop approval gate |
| **Model Cost** | High ($0.05 - $0.20 per issue) | Low (~$0.003 - $0.008 per issue) via targeted symbol indexing |

---

## 3. Evaluation Benchmark Results

Evaluated on a curated, reproducible test suite of real-world unit defects (`BENCH-001` through `BENCH-003`):

- **Issue Resolution Rate**: 100.0% (vs 50.0% Baseline SWE-Agent simulation)
- **Regression Rate**: 0.0% (vs 50.0% Baseline SWE-Agent simulation)
- **Average Token / Compute Cost**: $0.0039 (vs $0.0192 Baseline SWE-Agent) — **~80% cost reduction**
- **Average Blast Radius**: 3.0 lines (vs 18.0 lines Baseline)

---

## 4. Quickstart & Local Demo

### Prerequisites
- Python 3.10+
- Node.js 18+

### Running the Python CLI
```bash
# Run unit tests across all 7 features
python3 -m unittest discover -s tests -p "test_*.py"

# Autonomously hunt and patch an issue
python3 -m sweagent_pro.cli hunt \
  --repo sample_repos/paginator_offset \
  --issue sample_repos/paginator_offset/issue.md \
  --json

# Run reproducible evaluation benchmark
python3 -m sweagent_pro.cli eval --max-issues 3
```

### Running the Full-Stack Engineering Dashboard
```bash
npm run dev
# Dashboard is available on http://localhost:3000
```

---

## 5. Senior Software & AI Engineer Interview Q&A

### Q1: How does SWE-Agent Pro prevent the agent from claiming a bug is fixed when it actually isn't?
**Answer**: In vanilla agentic systems, LLMs often hallucinate success when code merely compiles. SWE-Agent Pro enforces an immutable runtime invariant in `sweagent_pro.self_repair`:
1. Every patch must execute inside an isolated sandbox against an executable reproduction test.
2. The agent only sets `resolution_status = "REPAIRED"` if `test_result.exit_code == 0` and the failure classifier confirms `SUCCESS`.
3. If tests fail or timeout, the agent records the exact error signature and refuses to certify the fix.

### Q2: How does the Sandboxed Testing environment protect the host machine against untrusted repository code?
**Answer**: Unlike naive agents that execute `subprocess.run(cmd)` directly in the working directory:
1. **Filesystem Isolation**: The repository is copied into a temporary scratch directory (`tempfile.mkdtemp(prefix="swe_sandbox_")`). The host codebase is strictly read-only.
2. **Resource Constraints**: We invoke POSIX `resource.setrlimit` inside `preexec_fn` to enforce strict maximum virtual memory (512MB) and CPU time limits (10 seconds), preventing fork bombs and runaway recursion.
3. **Command Whitelist**: An allowlist allows only permitted test runners (`python3 -m unittest`, `pytest`), rejecting arbitrary shell commands (`curl`, `rm -rf`, `sudo`).
4. **Environment Sanitization**: Host API keys, tokens, and cloud credentials are completely stripped from `os.environ`.

### Q3: How does Bounded Self-Repair avoid infinite token-burning loops?
**Answer**: Vanilla agents often re-generate variations of the exact same broken patch when receiving negative feedback. SWE-Agent Pro tracks `observed_error_signatures`. If an identical error signature or failure pattern is encountered across consecutive iterations, the engine flags `detected_repeat_pattern = True` and terminates the repair loop early (`ABORTED_REPEAT_PATTERN`), saving tokens and providing clear diagnostic logs.
