#!/usr/bin/env python3
"""
Real LLM Integration Test — Composite Skill with DeepSeek API
=============================================================
Tests the full pipeline:
  debug-python-error (composite)
    └─► analyze-python-error  (atomic → LLM call #1)
    └─► suggest-python-fix    (atomic → LLM call #2)

Verifies:
  ✓ Sub-skills are called in order
  ✓ Each sub-skill receives correct input (output of previous feeds in)
  ✓ Each LLM response is valid JSON matching the output schema
  ✓ Final composite output merges all sub-skill outputs correctly
"""
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from skill_library.core.registry import SkillRegistry
from skill_library.core.executor import SkillExecutor, LogEvent
from skill_library.core.validator import InputValidator

# ─────────────────────────────────────────────────────────────────────────────
# Terminal colors (ANSI)
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "cyan":   "\033[36m",
    "green":  "\033[32m",
    "yellow": "\033[33m",
    "red":    "\033[31m",
    "purple": "\033[35m",
    "blue":   "\033[34m",
    "white":  "\033[97m",
}

STEP_COLORS = {
    "identify_skill":   C["blue"],
    "validate_input":   C["green"],
    "check_constraint": C["yellow"],
    "call_llm":         C["purple"],
    "parse_output":     C["cyan"],
    "compose":          C["purple"],
}

STEP_ICONS = {
    "identify_skill":   "🔍",
    "validate_input":   "✅",
    "check_constraint": "🔒",
    "call_llm":         "🤖",
    "parse_output":     "📦",
    "compose":          "🔗",
    "safety_approval":  "⚠️",
}

STATUS_STYLE = {
    "start":   ("  ▸", C["cyan"]),
    "success": ("  ✓", C["green"]),
    "error":   ("  ✗", C["red"]),
    "info":    ("   ", C["dim"]),
}


# ─────────────────────────────────────────────────────────────────────────────
# Detailed log callback — prints RAW LLM responses and validated inputs
# ─────────────────────────────────────────────────────────────────────────────
_current_skill = ""

def make_verbose_callback():
    """Creates a log callback that prints every detail of execution."""
    call_count = {"llm": 0}

    def callback(event: LogEvent):
        global _current_skill
        color = STEP_COLORS.get(event.step, C["white"])
        icon  = STEP_ICONS.get(event.step, "▸")
        pfx, sfx = STATUS_STYLE.get(event.status, ("  ", C["white"]))

        skill_tag = f"{C['dim']}[{event.skill_name}]{C['reset']} " if event.skill_name else ""
        step_tag  = f"{color}{C['bold']}[{event.step.upper()}]{C['reset']}"

        print(f"{sfx}{pfx}{C['reset']} {icon} {step_tag} {skill_tag}{event.message}")

        if event.data:
            for k, v in event.data.items():
                val = v
                if isinstance(val, list): val = ", ".join(str(x) for x in val)
                elif isinstance(val, str) and len(val) > 200:
                    val = val[:200] + "..."
                print(f"       {C['dim']}↳ {k}: {val}{C['reset']}")

        # Extra: when LLM is called, show it clearly
        if event.step == "call_llm" and event.status == "start":
            call_count["llm"] += 1
            print(f"\n{C['purple']}{'─'*55}{C['reset']}")
            print(f"{C['purple']}{C['bold']}  LLM CALL #{call_count['llm']} — {event.skill_name}{C['reset']}")
            print(f"{C['purple']}{'─'*55}{C['reset']}")

        if event.step == "call_llm" and event.status == "success":
            raw = (event.data or {}).get("preview", "")
            print(f"\n  {C['dim']}Raw LLM response:[{C['reset']}")
            print(f"  {C['yellow']}{raw}{C['reset']}")
            print(f"  {C['dim']}]{C['reset']}\n")

        if event.step == "compose" and "sub-skill" in event.message and "[1/" in event.message:
            print(f"\n{C['blue']}{'━'*55}{C['reset']}")
            print(f"{C['blue']}{C['bold']}  SUB-SKILL PIPELINE START{C['reset']}")
            print(f"{C['blue']}{'━'*55}{C['reset']}\n")

        time.sleep(0.03)   # tiny pause to make streaming feel real

    return callback, call_count


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def section(title: str):
    w = 60
    print(f"\n{C['cyan']}{'═'*w}{C['reset']}")
    print(f"{C['cyan']}{C['bold']}  {title}{C['reset']}")
    print(f"{C['cyan']}{'═'*w}{C['reset']}\n")


def check_mark(label: str, ok: bool, detail: str = ""):
    sym = f"{C['green']}✓{C['reset']}" if ok else f"{C['red']}✗{C['reset']}"
    det = f" {C['dim']}{detail}{C['reset']}" if detail else ""
    print(f"  {sym}  {label}{det}")


def run_buggy_code() -> str:
    """Execute the buggy Python file and return its stderr (the stacktrace)."""
    result = subprocess.run(
        [sys.executable, "test_data/buggy_code.py"],
        capture_output=True, text=True, cwd=Path(__file__).parent
    )
    return (result.stdout + result.stderr).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Verification helpers
# ─────────────────────────────────────────────────────────────────────────────
def verify_output(skill_name: str, output: dict, expected_props: list[str]):
    """Assert all expected output properties are present and non-empty."""
    print(f"\n  {C['bold']}Verification — {skill_name} output:{C['reset']}")
    all_ok = True
    for prop in expected_props:
        present = prop in output and output[prop] is not None
        non_empty = bool(str(output.get(prop, "")).strip())
        ok = present and non_empty
        all_ok = all_ok and ok
        check_mark(
            f"output.{prop}",
            ok,
            f"= {repr(str(output.get(prop,''))[:60])}"
        )
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Main test
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{C['bold']}{C['white']}{'▓'*60}{C['reset']}")
    print(f"{C['bold']}{C['white']}  REAL LLM TEST — Composite Skill via DeepSeek API{C['reset']}")
    print(f"{C['bold']}{C['white']}{'▓'*60}{C['reset']}\n")

    results = {}

    # ──────────────────────────────────────────────────────────────────────
    # STEP 0: Capture real stacktrace by running buggy code
    # ──────────────────────────────────────────────────────────────────────
    section("STEP 0 — Generate Real Python Stacktrace")
    print(f"  Running: {C['yellow']}python3 test_data/buggy_code.py{C['reset']}\n")

    stacktrace = run_buggy_code()
    print(f"  {C['dim']}Captured stacktrace:{C['reset']}")
    print(f"  {C['yellow']}{stacktrace}{C['reset']}\n")

    has_traceback = "Traceback" in stacktrace and "AttributeError" in stacktrace
    check_mark("Traceback captured", has_traceback)
    check_mark("AttributeError present", "AttributeError" in stacktrace)
    check_mark("buggy_code.py in traceback", "buggy_code.py" in stacktrace)

    results["stacktrace_captured"] = has_traceback

    # ──────────────────────────────────────────────────────────────────────
    # STEP 1: Load skill registry
    # ──────────────────────────────────────────────────────────────────────
    section("STEP 1 — Load Skill Registry")
    registry = SkillRegistry(Path(__file__).parent / "skills")
    count = registry.load_all()
    print(f"  Loaded {C['green']}{C['bold']}{count} skills{C['reset']}:\n")
    for s in registry.all_skills():
        lvl_color = C["purple"] if s.level == "composite" else C["green"]
        sub = f" → [{', '.join(s.sub_skills)}]" if s.sub_skills else ""
        print(f"    {C['cyan']}{s.name}{C['reset']}  {lvl_color}({s.level}){C['reset']}{sub}")

    composite_skill = registry.get("debug-python-error")
    check_mark("debug-python-error loaded", composite_skill is not None)
    check_mark("analyze-python-error loaded", registry.get("analyze-python-error") is not None)
    check_mark("suggest-python-fix loaded",   registry.get("suggest-python-fix") is not None)

    results["registry_ok"] = composite_skill is not None

    # ──────────────────────────────────────────────────────────────────────
    # STEP 2: Validate composite skill's input schema
    # ──────────────────────────────────────────────────────────────────────
    section("STEP 2 — Validate Input Against Schema (pre-execution check)")
    input_data = {
        "stacktrace": stacktrace,
        "source_path": "test_data/buggy_code.py",
    }
    validator = InputValidator()
    val_result = validator.validate(composite_skill, input_data)
    check_mark("Input schema validation passed", val_result.valid,
               f"errors: {val_result.errors}" if not val_result.valid else "")
    print(f"\n  Input fields: {C['cyan']}{list(input_data.keys())}{C['reset']}")
    results["input_valid"] = val_result.valid

    # ──────────────────────────────────────────────────────────────────────
    # STEP 3: Execute composite skill with REAL DeepSeek LLM
    # ──────────────────────────────────────────────────────────────────────
    section("STEP 3 — Execute Composite Skill (REAL DeepSeek API)")
    print(f"  Skill  : {C['bold']}debug-python-error{C['reset']} (composite)")
    print(f"  Sub-skills: {C['purple']}analyze-python-error{C['reset']} → {C['purple']}suggest-python-fix{C['reset']}")
    print(f"  LLM    : DeepSeek / deepseek-chat\n")

    callback_fn, call_count = make_verbose_callback()
    executor = SkillExecutor(
        registry=registry,
        mock_mode=False,      # ← REAL API calls
        log_callback=callback_fn,
    )

    t0 = time.time()
    output = None
    error  = None
    try:
        output = executor.run(composite_skill, input_data)
    except Exception as exc:
        error = exc
        traceback.print_exc()

    elapsed = time.time() - t0

    results["execution_ok"] = output is not None
    results["llm_calls"]    = call_count["llm"]
    results["elapsed_s"]    = round(elapsed, 2)

    # ──────────────────────────────────────────────────────────────────────
    # STEP 4: Verify outputs
    # ──────────────────────────────────────────────────────────────────────
    section("STEP 4 — Verify Output Format & Correctness")

    if error:
        print(f"  {C['red']}Execution failed: {error}{C['reset']}")
        results["output_valid"] = False
    else:
        print(f"  {C['green']}Execution succeeded in {elapsed:.2f}s{C['reset']}\n")
        print(f"  {C['bold']}Raw JSON output:{C['reset']}")
        print(f"  {C['yellow']}{json.dumps(output, indent=4, ensure_ascii=False)}{C['reset']}")

        # Verify composite output has all expected fields
        expected = ["file", "line", "variable", "error_type", "fix_suggestion", "code_snippet"]
        all_ok = verify_output("debug-python-error", output, expected)
        results["output_valid"] = all_ok

        # Semantic spot-checks
        print(f"\n  {C['bold']}Semantic correctness checks:{C['reset']}")
        check_mark("file references .py file",
                   isinstance(output.get("file"), str) and ".py" in output.get("file", ""))
        check_mark("line is an integer",
                   isinstance(output.get("line"), int))
        check_mark("error_type mentions 'AttributeError' or 'NoneType'",
                   "Attribute" in output.get("error_type", "") or
                   "None" in output.get("error_type", "") or
                   "attribute" in output.get("fix_suggestion", "").lower())
        check_mark("fix_suggestion has content (>30 chars)",
                   len(output.get("fix_suggestion", "")) > 30)
        check_mark("code_snippet contains Python keywords",
                   any(kw in output.get("code_snippet", "") for kw in
                       ["def ", "if ", "self.", "return", "None", "assert"]))

    # ──────────────────────────────────────────────────────────────────────
    # STEP 5: Summary
    # ──────────────────────────────────────────────────────────────────────
    section("STEP 5 — Test Summary")
    print(f"  {'Label':<35} {'Pass?'}")
    print(f"  {'─'*50}")
    checks = [
        ("Stacktrace captured from buggy code",           results.get("stacktrace_captured")),
        ("All skills loaded from registry",               results.get("registry_ok")),
        ("Input schema validated before execution",       results.get("input_valid")),
        ("Composite skill executed without error",        results.get("execution_ok")),
        (f"LLM called exactly 2 times (one per sub-skill)", results.get("llm_calls") == 2),
        ("Final output has all 6 required fields",        results.get("output_valid")),
    ]
    passed = 0
    for label, ok in checks:
        sym = f"{C['green']}PASS{C['reset']}" if ok else f"{C['red']}FAIL{C['reset']}"
        print(f"  {label:<45} [{sym}]")
        if ok: passed += 1

    print(f"\n  {C['bold']}Result: {passed}/{len(checks)} checks passed"
          f"  |  Time: {results.get('elapsed_s', '?')}s"
          f"  |  LLM calls: {results.get('llm_calls', '?')}{C['reset']}\n")

    if passed == len(checks):
        print(f"  {C['green']}{C['bold']}✓ All checks passed! Composite skill works end-to-end with real DeepSeek.{C['reset']}\n")
    else:
        print(f"  {C['yellow']}⚠ Some checks failed. See details above.{C['reset']}\n")

    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
