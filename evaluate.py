#!/usr/bin/env python3
"""
evaluate.py — Skill Evaluation CLI
====================================
Evaluates AI agent skills via two methods:
  1. Doc Score  (SKILL.md documentation completeness, max 100pts)
  2. Test Cases (Run test cases, compute Pass Rate / Accuracy / Latency / Tokens)

Usage:
  python3 evaluate.py                              # evaluate all skills
  python3 evaluate.py --skill analyze-python-error # one skill
  python3 evaluate.py --skill analyze-python-error --doc-only
  python3 evaluate.py --skill analyze-python-error --mock
  python3 evaluate.py --skill analyze-python-error --consistency --runs 3
  python3 evaluate.py --all --out report.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from skill_library.core.registry import SkillRegistry
from skill_library.core.evaluator import SkillEvaluator, EvaluationReport
from skill_library.core.doc_reviewer import SkillDocReviewer

# ── ANSI colors ──────────────────────────────────────────────────────────────
C = {
    "green":  "\033[32m", "red":    "\033[31m", "yellow": "\033[33m",
    "cyan":   "\033[36m", "purple": "\033[35m", "blue":   "\033[34m",
    "bold":   "\033[1m",  "dim":    "\033[2m",  "reset":  "\033[0m",
    "white":  "\033[97m",
}


def section(title: str, width: int = 62):
    bar = "═" * width
    print(f"\n{C['cyan']}{bar}{C['reset']}")
    print(f"{C['cyan']}{C['bold']}  {title}{C['reset']}")
    print(f"{C['cyan']}{bar}{C['reset']}\n")


def metric_line(label: str, value: str, target: str, passed: bool | None = None):
    if passed is True:
        indicator = f"{C['green']}✓ {C['reset']}"
    elif passed is False:
        indicator = f"{C['red']}✗ {C['reset']}"
    else:
        indicator = "  "
    tgt = f"  {C['dim']}(target: {target}){C['reset']}" if target else ""
    print(f"  {indicator}{label:<28} {C['bold']}{value}{C['reset']}{tgt}")


def print_report(report: EvaluationReport, doc_result=None):
    """Pretty-print a full evaluation report to terminal."""
    verdict = (f"{C['green']}✅ PASS{C['reset']}" if report.pass_rate >= 80
               else f"{C['red']}❌ FAIL{C['reset']}")

    print(f"\n  {C['bold']}{C['white']}Skill: {report.skill_name}  v{report.skill_version}{C['reset']}  "
          f"  mode={C['yellow']}{'mock' if report.mock_mode else 'live-LLM'}{C['reset']}")

    # ── Doc Score ─────────────────────────────────────────────────────────────
    if doc_result:
        doc_verdict = (f"{C['green']}✅ PASS{C['reset']}" if doc_result.passed
                       else f"{C['red']}❌ FAIL{C['reset']}")
        print(f"\n  📄 Doc Score:   {C['bold']}{doc_result.total_score}/100{C['reset']}  {doc_verdict}")
        SkillDocReviewer.print_result(doc_result)

    # ── Test Case Results ─────────────────────────────────────────────────────
    print(f"\n  🧪 Test Cases ({report.total} total)\n")
    print(f"  {'ID':<10} {'Name':<38} {'Result':<8} {'Latency':>8}  {'Tokens':>7}")
    print(f"  {'-'*78}")
    for r in report.test_results:
        icon = f"{C['green']}PASS{C['reset']}" if r.passed else f"{C['red']}FAIL{C['reset']}"
        tok = r.token_usage.get("total", 0)
        print(f"  {r.tc_id:<10} {r.tc_name:<38} {icon}  {r.latency_ms:>7.0f}ms  {tok:>7}")
        if not r.passed:
            for c in r.criteria_results:
                if not c.passed:
                    print(f"       {C['red']}✗{C['reset']} {c.expression}")
                    if c.error:
                        print(f"           └─ {C['dim']}{c.error}{C['reset']}")
            if r.error:
                print(f"       {C['red']}✗ Execution: {r.error}{C['reset']}")

    # ── Aggregate Metrics ─────────────────────────────────────────────────────
    print(f"\n  📊 Aggregated Metrics\n")
    checks = report.metric_checks

    metric_line("Pass Rate",
                f"{report.pass_rate:.1f}%  ({report.passed}/{report.total})",
                "≥ 80%", checks.get("pass_rate"))
    metric_line("Accuracy (field-level)",
                f"{report.accuracy:.1f}%",
                "≥ 85%", checks.get("accuracy"))
    metric_line("Latency P50",
                f"{report.latency_p50:.0f} ms",
                "—")
    metric_line("Latency P95",
                f"{report.latency_p95:.0f} ms",
                "< 8000ms", checks.get("latency_p95"))
    metric_line("Avg Token Usage",
                f"{report.avg_tokens:.0f} tokens/call",
                "< 1000", checks.get("token_usage"))
    metric_line("Retry Rate",
                f"{report.retry_rate:.1f}%",
                "< 10%", checks.get("retry_rate"))
    if report.consistency_score is not None:
        metric_line("Consistency Score",
                    f"{report.consistency_score:.1f}%",
                    "≥ 90%", report.consistency_score >= 90)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n  {'─'*62}")
    print(f"  Overall:  {C['bold']}{report.passed}/{report.total} test cases passed{C['reset']}  {verdict}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Evaluate AI agent skills (Doc Score + Test Case execution)"
    )
    parser.add_argument("--skill", "-s", help="Skill name to evaluate (default: all)")
    parser.add_argument("--all", "-a", action="store_true", help="Evaluate all skills")
    parser.add_argument("--doc-only", action="store_true", help="Run Doc Score review only, skip test execution")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM (no API calls, no cost)")
    parser.add_argument("--consistency", action="store_true", help="Run consistency check for first test case")
    parser.add_argument("--runs", type=int, default=3, help="Number of consistency runs (default: 3)")
    parser.add_argument("--out", "-o", help="Write JSON report to file")
    parser.add_argument("--skills-dir", default="skills", help="Skills directory (default: skills/)")
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    registry = SkillRegistry(skills_dir)
    count = registry.load_all()
    print(f"\n  {C['bold']}Skill Evaluation Engine{C['reset']}  |  {count} skills loaded")

    # Determine which skills to evaluate
    if args.skill:
        skill = registry.get(args.skill)
        if skill is None:
            print(f"{C['red']}  Error: Skill '{args.skill}' not found.{C['reset']}")
            print(f"  Available: {list(registry.skills.keys())}")
            sys.exit(1)
        targets = [skill]
    else:
        targets = list(registry.all_skills())
        # Skip skills with no test cases unless doc-only
        if not args.doc_only:
            no_tc = [s for s in targets if not s.test_cases]
            if no_tc:
                print(f"\n  {C['yellow']}⚠ Skipping skills with no test_cases: "
                      f"{[s.name for s in no_tc]}{C['reset']}")
            targets = [s for s in targets if s.test_cases or args.doc_only]

    if not targets:
        print(f"  {C['yellow']}No skills to evaluate.{C['reset']}")
        sys.exit(0)

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    mock_mode = args.mock or not api_key
    if not api_key and not args.mock:
        print(f"  {C['yellow']}⚠ DEEPSEEK_API_KEY not set — switching to mock mode.{C['reset']}")

    reviewer = SkillDocReviewer()
    evaluator = SkillEvaluator(
        registry=registry,
        api_key=api_key,
        mock_mode=mock_mode,
        verbose=True,
    )

    all_reports = []

    for skill in targets:
        section(f"Evaluating: {skill.name}")

        # ── Doc Score ─────────────────────────────────────────────────────────
        doc_result = reviewer.review(skill)

        if args.doc_only:
            SkillDocReviewer.print_result(doc_result)
            all_reports.append({"skill": skill.name, "doc_score": doc_result.to_dict()})
            continue

        # ── Test Case Execution ───────────────────────────────────────────────
        if not skill.test_cases:
            print(f"  {C['yellow']}⚠ No test_cases defined — skipping execution.{C['reset']}")
            all_reports.append({"skill": skill.name, "doc_score": doc_result.to_dict()})
            continue

        print(f"  Running {len(skill.test_cases)} test case(s)  "
              f"[mode: {C['yellow']}{'mock' if mock_mode else 'DeepSeek live'}{C['reset']}]\n")

        report = evaluator.evaluate(skill)

        # ── Consistency check ─────────────────────────────────────────────────
        if args.consistency and skill.test_cases:
            tc = skill.test_cases[0]
            print(f"\n  🔄 Consistency check: '{tc.name}'  ({args.runs} runs)…")
            score = evaluator.consistency_check(skill, tc, runs=args.runs)
            report.consistency_score = score

        print_report(report, doc_result)

        all_reports.append({
            "skill": skill.name,
            "doc_score": doc_result.to_dict(),
            "test_execution": report.to_dict(),
        })

    # ── Write JSON output ─────────────────────────────────────────────────────
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(all_reports, indent=2, ensure_ascii=False))
        print(f"\n  📁 Report saved → {out_path}")

    # ── Final summary ─────────────────────────────────────────────────────────
    if len(all_reports) > 1 and not args.doc_only:
        section("Summary — All Skills")
        print(f"  {'Skill':<35} {'Doc':>5}  {'Pass Rate':>10}  {'P95 (ms)':>10}")
        print(f"  {'-'*65}")
        for r in all_reports:
            doc = r.get("doc_score", {}).get("doc_score", "—")
            te = r.get("test_execution", {})
            pr = te.get("summary", {}).get("pass_rate_pct", "—")
            p95 = te.get("metrics", {}).get("latency_p95_ms", "—")
            skill_name = r["skill"]
            print(f"  {skill_name:<35} {doc:>5}  {str(pr)+' %':>10}  {str(p95)+' ms':>10}")


if __name__ == "__main__":
    main()
