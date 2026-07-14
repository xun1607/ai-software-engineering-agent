from services.skill_testing.core.execution_models import ExecutionRequest, ExecutionResult

class ExecutionRuntime:
    """Môi trường thực thi kỹ năng vật lý (AG2 Execution Engine)"""
    @staticmethod
    async def execute(skill_client, request: ExecutionRequest) -> ExecutionResult:
        print(f"🤖 [SYSTEM ACTION] ->Thực thi kỹ năng '{request.skill_name}' qua Client...")
        
        # Execute skill via SkillExecutionClient
        raw_res = await skill_client.execute_skill(request.skill_name, request.args)
        
        # Parse into standard ExecutionResult contract
        # SkillResult to_dict returns {"status": ..., "stdout": ..., "stderr": ..., "message": ...}
        # We can extract the fields directly
        status = raw_res.status if hasattr(raw_res, "status") else raw_res.get("status", "FAILED")
        stdout = raw_res.stdout if hasattr(raw_res, "stdout") else raw_res.get("stdout", "")
        stderr = raw_res.stderr if hasattr(raw_res, "stderr") else raw_res.get("stderr", "")
        message = raw_res.message if hasattr(raw_res, "message") else raw_res.get("message", "")
        
        # Collect any extra properties as data dict
        data = {}
        if not hasattr(raw_res, "status") and isinstance(raw_res, dict):
            data = {k: v for k, v in raw_res.items() if k not in ["status", "stdout", "stderr", "message"]}
        elif hasattr(raw_res, "data"):
            data = raw_res.data
            
        return ExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            message=message,
            data=data
        )
