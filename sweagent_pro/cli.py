"""
Command Line Interface (CLI) for SWE-Agent Pro
"""

import argparse
import json
import sys
from pathlib import Path
from sweagent_pro.engine.coordinator import SWEAgentProCoordinator
from sweagent_pro.benchmark import SWEBenchmarkSuite


def main():
    parser = argparse.ArgumentParser(
        prog="sweagent-pro",
        description="SWE-Agent Pro: Autonomous Bug Hunter & Fixer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Command: hunt
    hunt_parser = subparsers.add_parser("hunt", help="Autonomously hunt and repair a bug in a repo")
    hunt_parser.add_argument("--repo", required=True, help="Path to repository snapshot")
    hunt_parser.add_argument("--issue", required=True, help="Bug report text or path to markdown/text file")
    hunt_parser.add_argument("--issue-id", default=None, help="Optional custom issue ID")
    hunt_parser.add_argument("--test-cmd", default=None, help="Custom test command to run")
    hunt_parser.add_argument("--json", action="store_true", help="Output raw JSON results")

    # Command: eval
    eval_parser = subparsers.add_parser("eval", help="Run reproducible evaluation benchmark")
    eval_parser.add_argument("--max-issues", type=int, default=3, help="Max issues to benchmark")
    eval_parser.add_argument("--json", action="store_true", help="Output raw JSON benchmark results")

    args = parser.parse_args()

    if args.command == "hunt":
        issue_text = args.issue
        if Path(args.issue).exists():
            issue_text = Path(args.issue).read_text(encoding="utf-8")

        coordinator = SWEAgentProCoordinator()
        state = coordinator.run_hunt(
            raw_issue=issue_text,
            repo_path=args.repo,
            issue_id=args.issue_id,
            test_command=args.test_cmd
        )

        state_dict = state.to_dict()

        if args.json:
            print(json.dumps(state_dict, indent=2))
        else:
            print("==================================================")
            print(f"SWE-Agent Pro Run Result: {state.run_id}")
            print(f"Status: {state.status}")
            print(f"Issue: [{state.issue.id}] {state.issue.title}")
            print(f"Evidence Found: {len(state.trace.evidence)} locations")
            print(f"Top Hypothesis: {state.hypotheses[0].title if state.hypotheses else 'None'}")
            if state.current_patch:
                print(f"Generated Patch: {state.current_patch.patch_id} (Blast Radius: {state.current_patch.blast_radius_score})")
            if state.regression_report:
                print(f"Regression Safe: {state.regression_report.safe_to_merge}")
            print("==================================================")

    elif args.command == "eval":
        suite = SWEBenchmarkSuite()
        results = suite.run_benchmark(max_issues=args.max_issues)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("==================================================")
            print("SWE-Agent Pro vs Baseline SWE-Agent Benchmark")
            print("==================================================")
            print(f"Issues Evaluated: {results['summary']['dataset_size']}")
            print(f"SWE-Agent Pro Resolution Rate: {results['summary']['pro']['resolution_rate_percent']}%")
            print(f"Baseline Resolution Rate:      {results['summary']['baseline']['resolution_rate_percent']}%")
            print(f"SWE-Agent Pro Regression Rate: {results['summary']['pro']['regression_rate_percent']}%")
            print(f"Baseline Regression Rate:      {results['summary']['baseline']['regression_rate_percent']}%")
            print("==================================================")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
