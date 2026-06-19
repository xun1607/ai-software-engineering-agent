from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import json
import asyncio
from services.skill_testing.core.llm_client import OpenAIClient
from services.skill_testing.core.skill_client import SkillExecutionClient
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.benchmark_runner import (
    WorkspaceManager,
    BugInjector,
    PreValidator,
    run_cass_orchestrator,
    verify_solution
)

# Available mock tools index to build the semantic registry
MOCK_TOOLS_LIST = [
    {"name": "analyze-stacktrace", "description": "Phân tích java stacktrace", "skill_id": "analyze-stacktrace"},
    {"name": "read-code-context", "description": "Đọc mã nguồn Java xung quanh dòng chỉ định", "skill_id": "read-code-context"},
    {"name": "suggest-java-fix", "description": "Ghi đè bản vá lỗi Java", "skill_id": "suggest-java-fix"},
    {"name": "debug-java-null-pointer", "description": "Biên dịch javac kiểm tra lỗi cú pháp Java", "skill_id": "debug-java-null-pointer"}
]

async def main():
    print("🎬 Starting demo run for TC_002_Petclinic_MissingImport...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        return
        
    ws_manager = WorkspaceManager()
    bug_injector = BugInjector()
    llm_client = OpenAIClient(api_key=api_key)
    
    # Initialize the registry index
    semantic_registry.build_index(MOCK_TOOLS_LIST)
    
    tc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "testcases", "TC_002_Petclinic_MissingImport"))
    with open(os.path.join(tc_dir, "testcase.json"), "r", encoding="utf-8") as f:
        tc_data = json.load(f)
    with open(os.path.join(tc_dir, "expected.json"), "r", encoding="utf-8") as f:
        expected_data = json.load(f)
        
    # 1. Setup workspace
    workspace_path = ws_manager.setup_workspace(
        repo_root_rel=tc_data["repo_root"],
        testcase_id="TC_002_Petclinic_MissingImport",
        mode="cass_orchestrator",
        run_id="demo"
    )
    
    # 2. Inject bug
    bug_injector.inject(workspace_path, tc_data["bug_injection"])
    
    # 3. Pre-validate (sanity check that project build fails due to missing import)
    pre_valid = PreValidator.validate(
        workspace_path=workspace_path,
        bug_type=tc_data["bug_type"],
        build_cmd=tc_data["build_command"],
        val_cmd=tc_data["validation_command"]
    )
    print(f"Pre-validation outcome: {pre_valid}")
    if not pre_valid:
        print("Pre-validation failed! Aborting run.")
        ws_manager.destroy_workspace(workspace_path)
        return
        
    # 4. Run proposed CASS Orchestrator
    skill_client = SkillExecutionClient(workspace_path=workspace_path)
    metrics = await run_cass_orchestrator(workspace_path, tc_data, llm_client, skill_client)
    
    # 5. Post-validation check
    passed, validation_err = verify_solution(workspace_path, expected_data)
    metrics["passed"] = passed
    print(f"Post-validation result: {'✅ PASSED' if passed else '❌ FAILED'} | error: {validation_err}")
    
    # Print clean summary
    print("\n" + "="*80)
    print("📈 DEMO RUN SUMMARY")
    print("="*80)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    
    # Clean up workspace
    ws_manager.destroy_workspace(workspace_path)

if __name__ == "__main__":
    asyncio.run(main())
