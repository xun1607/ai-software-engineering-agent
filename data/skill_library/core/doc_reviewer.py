"""
SkillDocReviewer — Evaluates SKILL.md documentation completeness (Doc Score).

Scoring: 100 points across 11 criteria mapped to the 5-layer framework.
Threshold: Doc Score ≥ 80 → PASS
"""
import re
from dataclasses import dataclass, field
from typing import List, Tuple

from ..models.skill import Skill


@dataclass
class DocCriterion:
    id: str
    layer: str
    description: str
    points: int
    passed: bool = False
    note: str = ""


@dataclass
class DocScoreResult:
    skill_name: str
    total_score: int
    max_score: int = 100
    passed: bool = False            # score >= threshold
    threshold: int = 80
    criteria: List[DocCriterion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "doc_score": self.total_score,
            "max_score": self.max_score,
            "passed": self.passed,
            "threshold": self.threshold,
            "criteria": [
                {
                    "id": c.id,
                    "layer": c.layer,
                    "description": c.description,
                    "points": c.points,
                    "passed": c.passed,
                    "note": c.note,
                }
                for c in self.criteria
            ],
        }


class SkillDocReviewer:
    """
    Automatically scores a Skill's SKILL.md against the 5-layer framework.

    Usage:
        reviewer = SkillDocReviewer()
        result = reviewer.review(skill)
        print(result.total_score)   # e.g. 87
    """

    THRESHOLD = 80

    # ── Scoring criteria (id, layer, description, points, checker_method) ────
    CRITERIA: List[Tuple[str, str, str, int, str]] = [
        # id        layer              description                              pts  method
        ("D01", "Spec",     "`goal` field present and non-empty",              5,   "_check_goal"),
        ("D02", "Spec",     "`description` has ≥ 15 words",                   5,   "_check_description"),
        ("D03", "Spec",     "`input` has `required` fields defined",           10,  "_check_input"),
        ("D04", "Spec",     "`output` has `properties` defined",               10,  "_check_output"),
        ("D05", "Spec",     "`constraints.resources.timeout` set",             5,   "_check_timeout"),
        ("D06", "Spec",     "`acceptance_criteria` has ≥ 2 criteria",          15,  "_check_acceptance"),
        ("D07", "Spec",     "`metrics` defines ≥ 2 metric targets",            10,  "_check_metrics"),
        ("D08", "Design",   "`reasoning_strategy` set (not default empty)",    10,  "_check_reasoning"),
        ("D09", "Design",   "`## Examples` section OR `examples` metadata ≥1", 10,  "_check_examples"),
        ("D10", "Eval",     "`test_cases` has ≥ 2 test cases",                 15,  "_check_test_cases"),
        ("D11", "Design",   "`fallback_strategy` set and non-empty",           5,   "_check_fallback"),
    ]

    def review(self, skill: Skill) -> DocScoreResult:
        results: List[DocCriterion] = []
        total = 0
        for crit_id, layer, desc, pts, method in self.CRITERIA:
            checker = getattr(self, method)
            passed, note = checker(skill)
            results.append(DocCriterion(
                id=crit_id, layer=layer, description=desc,
                points=pts, passed=passed, note=note,
            ))
            if passed:
                total += pts

        return DocScoreResult(
            skill_name=skill.name,
            total_score=total,
            max_score=100,
            passed=total >= self.THRESHOLD,
            threshold=self.THRESHOLD,
            criteria=results,
        )

    # ── Individual checkers ───────────────────────────────────────────────────
    def _check_goal(self, s: Skill) -> Tuple[bool, str]:
        ok = bool(s.goal and s.goal.strip())
        return ok, "" if ok else "Add `goal: \"...\"` to SKILL.md frontmatter"

    def _check_description(self, s: Skill) -> Tuple[bool, str]:
        words = len(s.description.split())
        ok = words >= 15
        return ok, f"{words} words" + ("" if ok else " — need ≥ 15")

    def _check_input(self, s: Skill) -> Tuple[bool, str]:
        required = s.input.get("required", [])
        ok = len(required) >= 1
        return ok, f"{len(required)} required field(s)" + ("" if ok else " — add `required:` list")

    def _check_output(self, s: Skill) -> Tuple[bool, str]:
        props = s.output.get("properties", {})
        ok = len(props) >= 1
        return ok, f"{len(props)} output property(ies)" + ("" if ok else " — add `properties:` dict")

    def _check_timeout(self, s: Skill) -> Tuple[bool, str]:
        t = s.constraints.resources.timeout
        ok = bool(t and t != "60s" or t == "60s")   # any value is fine
        ok = bool(t)
        return ok, f"timeout={t}" if ok else "Add `constraints.resources.timeout`"

    def _check_acceptance(self, s: Skill) -> Tuple[bool, str]:
        n = len(s.acceptance_criteria)
        ok = n >= 2
        return ok, f"{n} criterion(a)" + ("" if ok else " — add ≥ 2 `acceptance_criteria` items")

    def _check_metrics(self, s: Skill) -> Tuple[bool, str]:
        n = len(s.metrics)
        ok = n >= 2
        return ok, f"{n} metric(s)" + ("" if ok else " — define ≥ 2 entries under `metrics:`")

    def _check_reasoning(self, s: Skill) -> Tuple[bool, str]:
        ok = bool(s.reasoning_strategy)
        return ok, f"strategy={s.reasoning_strategy}" if ok else "Add `reasoning_strategy:` field"

    def _check_examples(self, s: Skill) -> Tuple[bool, str]:
        # Check metadata examples OR body section
        if s.examples:
            return True, f"{len(s.examples)} example(s) in metadata"
        # Check for ## Examples section in skill_dir/SKILL.md
        if s.skill_dir:
            md_path = s.skill_dir / "SKILL.md"
            if md_path.exists():
                content = md_path.read_text()
                if re.search(r"##\s+Examples?", content, re.IGNORECASE):
                    return True, "## Examples section found in body"
        return False, "Add `examples:` metadata or `## Examples` section"

    def _check_test_cases(self, s: Skill) -> Tuple[bool, str]:
        n = len(s.test_cases)
        ok = n >= 2
        return ok, f"{n} test case(s)" + ("" if ok else " — add ≥ 2 entries under `test_cases:`")

    def _check_fallback(self, s: Skill) -> Tuple[bool, str]:
        ok = bool(s.fallback_strategy and s.fallback_strategy.strip())
        return ok, "" if ok else "Add `fallback_strategy:` field"

    # ── Pretty print ──────────────────────────────────────────────────────────
    @staticmethod
    def print_result(result: DocScoreResult, use_color: bool = True) -> None:
        C = {
            "green": "\033[32m", "red": "\033[31m", "yellow": "\033[33m",
            "cyan": "\033[36m", "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m",
        } if use_color else {k: "" for k in ["green", "red", "yellow", "cyan", "dim", "bold", "reset"]}

        verdict = (f"{C['green']}✅ PASS{C['reset']}" if result.passed
                   else f"{C['red']}❌ FAIL{C['reset']}")
        print(f"\n  📄 Doc Score: {C['bold']}{result.total_score}/{result.max_score}{C['reset']}  {verdict}")
        print(f"     (threshold: {result.threshold}/100)\n")

        prev_layer = ""
        for c in result.criteria:
            if c.layer != prev_layer:
                print(f"  {C['dim']}── Layer: {c.layer} ──────────────────────────────{C['reset']}")
                prev_layer = c.layer
            sym = f"{C['green']}✓{C['reset']}" if c.passed else f"{C['red']}✗{C['reset']}"
            pts = f"+{c.points}pts" if c.passed else f" {c.points}pts"
            note = f"  {C['dim']}{c.note}{C['reset']}" if c.note else ""
            print(f"  {sym} [{pts:>5}]  {c.description}{note}")
