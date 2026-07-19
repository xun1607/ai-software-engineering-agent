import time
from typing import Dict, Any, List, Tuple
from swe_agent.skills.base import AgentSkill
from swe_agent.core.base import AbstractSandbox

class DotDict(dict):
    """
    Helper dict wrapper to allow dot notation access in evaluation expressions.
    """
    def __getattr__(self, name):
        try:
            val = self[name]
            if isinstance(val, dict):
                return DotDict(val)
            return val
        except KeyError:
            raise AttributeError(name)

class SkillValidator:
    """
    Testbed Validator for verifying Agent Skills 
    Evaluates safety, correctness, latency, and determines if a skill is verified.
    """
    def __init__(self, sandbox: AbstractSandbox):
        self.sandbox = sandbox

    def validate_skill(self, skill: AgentSkill, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a skill against a list of test cases in the sandbox environment.
        Returns validation report containing pass rate, average latency, and verification status.
        """
        passed_count = 0
        total_latency = 0.0
        results = []

        print(f"\n[Testbed] Validating Skill: '{skill.name}'...")

        for tc in test_cases:
            tc_id = tc.get("id", "unknown")
            tc_name = tc.get("name", "Unnamed Test Case")
            tc_input = tc.get("input", {})
            expected = tc.get("expected_output", {})
            acceptance_criteria = tc.get("acceptance", [])

            print(f"  - Running Test Case: {tc_id} ({tc_name})...")
            
            start_time = time.time()
            error_msg = None
            output = None
            passed = False

            try:
                output_raw = skill.execute(self.sandbox, **tc_input)
                
                if isinstance(output_raw, str):
                    try:
                        import json
                        output = json.loads(output_raw)
                    except Exception:
                        output = {"result": output_raw}
                else:
                    output = output_raw
                
                passed = True
                for expr in acceptance_criteria:
                    try:
                        allowed_locals = {
                            "output": DotDict(output) if isinstance(output, dict) else output,
                            "expected": DotDict(expected) if isinstance(expected, dict) else expected,
                            "abs": abs,
                            "len": len,
                            "str": str,
                            "int": int
                        }
                        # Evaluate expression in restricted namespace
                        expr_res = eval(expr, {"__builtins__": None}, allowed_locals)
                        if not expr_res:
                            passed = False
                            error_msg = f"Criteria failed: {expr}"
                            break
                    except Exception as eval_err:
                        passed = False
                        error_msg = f"Criteria eval error on '{expr}': {str(eval_err)}"
                        break

            except Exception as run_err:
                passed = False
                error_msg = f"Skill execution error: {str(run_err)}"

            latency_ms = (time.time() - start_time) * 1000
            total_latency += latency_ms

            if passed:
                passed_count += 1

            results.append({
                "test_case_id": tc_id,
                "passed": passed,
                "latency_ms": round(latency_ms, 2),
                "error": error_msg
            })

            status_str = "PASS" if passed else f"FAIL ({error_msg})"
            print(f"    => Status: {status_str} | Latency: {latency_ms:.2f}ms")

        total_tests = len(test_cases)
        pass_rate = (passed_count / total_tests) * 100 if total_tests > 0 else 0.0
        avg_latency = total_latency / total_tests if total_tests > 0 else 0.0

        # Skill is verified if pass rate >= 75%
        is_verified = pass_rate >= 75.0

        report = {
            "skill_name": skill.name,
            "pass_rate": round(pass_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "is_verified": is_verified,
            "results": results
        }
        
        print(f"[Testbed] Validation Complete. Verified: {is_verified} | Pass Rate: {pass_rate:.1f}%")
        return report
