import os
import json
import httpx
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List

from services.skill_testing.orchestrator import (
    api_key,
    get_compiled_workflow,
    semantic_registry
)
from services.skill_testing.core.skill_client import SkillExecutionClient
from services.skill_testing.core.llm_client import OpenAIClient

app = FastAPI(title="AG2 Orchestrator Server", version="1.0.0")

# Cấu hình CORSMiddleware kết nối với Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Cơ chế Caching thông minh (Global Cache) cho danh sách Skills
_SKILL_CACHE = {"tools": None}

async def get_cached_skills() -> List[Dict[str, Any]]:
    """Lấy danh sách skills từ Cache (RAM) hoặc gọi sang AG1 nếu chưa có."""
    if _SKILL_CACHE["tools"] is not None:
        print("⚡ [CACHE HIT] Tải danh sách kỹ năng trực tiếp từ RAM cache.")
        return _SKILL_CACHE["tools"]

    print("🌐 [CACHE MISS] Gọi API AG1 (cổng 8001) để lấy danh sách kỹ năng.")
    AG1_TOOLS_ENDPOINT = "http://127.0.0.1:8001/skills/tools"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(AG1_TOOLS_ENDPOINT, timeout=10.0)
            if response.status_code == 200:
                tools_data = response.json()
                _SKILL_CACHE["tools"] = tools_data
                print(f"✅ [CACHE] Đã nạp và lưu bộ đệm thành công {len(tools_data)} kỹ năng từ AG1.")
                return tools_data
            else:
                print(f"⚠️ [CACHE] AG1 trả về status code {response.status_code}. Kích hoạt fallback.")
    except Exception as e:
        print(f"❌ [CACHE] Thất bại khi kết nối tới AG1 ({str(e)}). Kích hoạt fallback.")

    # Mảng fallback dự phòng khi AG1 offline
    print("🔌 [OFFLINE FALLBACK] Sử dụng danh sách kỹ năng giả lập cục bộ (Mock).")
    mock_tools = [
        {"name": "analyze-stacktrace", "description": "Phân tích java stacktrace để xác định điểm NPE", "skill_id": "analyze-stacktrace"},
        {"name": "read-code-context", "description": "Đọc mã nguồn Java xung quanh dòng chỉ định", "skill_id": "read-code-context"},
        {"name": "suggest-java-fix", "description": "Ghi đè bản vá lỗi Java", "skill_id": "suggest-java-fix"},
        {"name": "debug-java-null-pointer", "description": "Biên dịch javac kiểm tra lỗi cú pháp Java", "skill_id": "debug-java-null-pointer"}
    ]
    _SKILL_CACHE["tools"] = mock_tools
    return mock_tools


# 2. Định nghĩa Pydantic BaseModel cho Payload đầu vào
class OrchestratePayload(BaseModel):
    code_content: str
    filename: str
    stacktrace: str
    message: str


# 3. Endpoint POST luân chuyển trạng thái đồ thị qua SSE (Server-Sent Events)
@app.post("/api/orchestrate/stream")
async def orchestrate_stream(payload: OrchestratePayload, request: Request):
    print(f"🚀 [ORCHESTRATE] Tiếp nhận yêu cầu chạy pipeline cho file: {payload.filename}")
 
    tools_data = await get_cached_skills()
  
    if semantic_registry._embeddings is None:
        semantic_registry.build_index(tools_data)
    else:
        print("⚡ [REGISTRY] Bỏ qua xây dựng index vector vì Registry đã được lập chỉ mục trước đó.")
    

    skill_client = SkillExecutionClient()
    skill_client.setup_initial_workspace(payload.code_content, payload.filename)
    
    llm_client = OpenAIClient(api_key=api_key)
    compiled_app = get_compiled_workflow(llm_client, skill_client)

    initial_state = {
        "user_context": {
            "code": payload.code_content,
            "stacktrace": payload.stacktrace,
            "message": payload.message
        },
        "plan": [],
        "current_step_idx": 0,
        "step_count": 0,
        "history": []
    }

    async def event_generator():
        running_state = dict(initial_state)
        
        try:
            print("📡 [STREAM] Khởi tạo luồng truyền dữ liệu thời gian thực (SSE)...")
            async for event in compiled_app.astream(initial_state):
                if await request.is_disconnected():
                    print("🔌 [STREAM] Client đã ngắt kết nối. Hủy tiến trình chạy đồ thị và giải phóng tài nguyên.")
                    break
                node_name = list(event.keys())[0]
                node_update = event[node_name]
                
                for k, v in node_update.items():
                    running_state[k] = v
                
                clean_state = {
                    "node": node_name,
                    "step_count": running_state.get("step_count", 0),
                    "current_step_idx": running_state.get("current_step_idx", 0),
                    "plan": running_state.get("plan", []),
                    "last_observation": running_state.get("last_observation", ""),
                    "is_finished": running_state.get("is_finished", False),
                    "final_answer": running_state.get("final_answer", "")
                }
                
                print(f"🔹 [NODE FINISHED] Node '{node_name}' đã thực thi xong. Gửi trạng thái qua SSE...")
                yield f"data: {json.dumps(clean_state, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            print(f"❌ [STREAM ERROR] Có lỗi xảy ra trong luồng: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            print("🏁 [STREAM] Đã đóng luồng SSE.")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/orchestrate/run-test-suite")
async def run_test_suite(request: Request):
    async def event_generator():
        import glob
        import time
        from services.skill_testing.orchestrator import run_pipeline

        testcases_path = os.path.join(os.path.dirname(__file__), "testcases.json")
        if not os.path.exists(testcases_path):
            yield f"data: {json.dumps({'error': 'Không tìm thấy file testcases.json'}, ensure_ascii=False)}\n\n"
            return

        with open(testcases_path, "r", encoding="utf-8") as f:
            testcases = json.load(f)

        # 1. Nạp kỹ năng và chỉ mục nếu chưa có
        tools_data = await get_cached_skills()
        if semantic_registry._embeddings is None:
            semantic_registry.build_index(tools_data)

        client = SkillExecutionClient()
        workspace_dir = client.workspace_dir
        java_src_dir = client.java_src_dir

        results = []
        suite_start_time = time.time()

        try:
            for tc in testcases:
                if await request.is_disconnected():
                    print("🔌 [STREAM] Client disconnected, aborting test suite run.")
                    break

                tc_id = tc["id"]
                filename = tc["filename"]
                code_content = tc["code_content"]
                stacktrace = tc["stacktrace"]
                message = tc["message"]

                # Gửi sự kiện RUNNING đầu tiên
                yield f"data: {json.dumps({'status': 'RUNNING', 'id': tc_id, 'message': 'Đang chuẩn bị môi trường...'}, ensure_ascii=False)}\n\n"

                # Dọn dẹp môi trường (xóa toàn bộ file .java rác trong thư mục nguồn và file .py cũ trong workspace)
                old_files = glob.glob(os.path.join(java_src_dir, "*.java")) + glob.glob(os.path.join(workspace_dir, "*.py"))
                for fpath in old_files:
                    try:
                        os.remove(fpath)
                    except Exception as e:
                        print(f"⚠️ Không thể xóa file {fpath}: {e}")

                # Ghi code ban đầu vào workspace
                client.setup_initial_workspace(code_content, filename)

                tc_start_time = time.time()

                initial_state = {
                    "user_context": {
                        "code": code_content,
                        "stacktrace": stacktrace,
                        "message": message,
                        "current_skill_metadata": {}
                    },
                    "plan": [],
                    "current_step_idx": 0,
                    "step_count": 0,
                    "history": []
                }

                llm_client = OpenAIClient(api_key=api_key)
                compiled_app = get_compiled_workflow(llm_client, client)

                running_state = dict(initial_state)

                try:
                    # Chạy astream của LangGraph cho testcase hiện tại để bắt các bước trung gian
                    async for event in compiled_app.astream(initial_state):
                        if await request.is_disconnected():
                            break

                        node_name = list(event.keys())[0]
                        node_update = event[node_name]

                        # Cập nhật trạng thái
                        for k, v in node_update.items():
                            running_state[k] = v

                        # Bắn thông tin bước hiện tại về Frontend
                        step_data = {
                            "status": "STEP",
                            "id": tc_id,
                            "node": node_name,
                            "step_count": running_state.get("step_count", 0),
                            "current_step_idx": running_state.get("current_step_idx", 0),
                            "plan": running_state.get("plan", []),
                            "last_observation": running_state.get("last_observation", ""),
                            "selected_skill": running_state.get("selected_skill", "")
                        }
                        yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"

                    # Khi kết thúc testcase
                    elapsed_time = time.time() - tc_start_time
                    is_finished = running_state.get("is_finished", False)
                    final_answer = running_state.get("final_answer", "")
                    step_count = running_state.get("step_count", 0)

                    passed = False
                    expected_out = tc.get("expected_output", "")
                    target_file_path = os.path.join(java_src_dir if filename.endswith(".java") else workspace_dir, filename)
                    
                    if os.path.exists(target_file_path) and os.path.getsize(target_file_path) > 0:
                        if expected_out == "compilation_success" and filename.endswith(".java"):
                            import subprocess
                            java_files = glob.glob(os.path.join(client.java_src_dir, "*.java"))
                            rel_paths = [os.path.relpath(p, client.workspace_dir) for p in java_files]
                            comp_res = subprocess.run(
                                ["javac"] + rel_paths,
                                cwd=client.workspace_dir,
                                capture_output=True,
                                text=True
                            )
                            if comp_res.returncode == 0:
                                passed = True
                                print(f"🎯 [API XÁC THỰC VẬT LÝ] {tc_id}: Biên dịch javac thành công!")
                            else:
                                print(f"❌ [API XÁC THỰC VẬT LÝ] {tc_id}: Biên dịch javac thất bại!")
                        elif expected_out == "execution_success":
                            import subprocess
                            import sys
                            python_exe = os.path.join(os.path.dirname(client.workspace_dir), "venv", "Scripts", "python.exe")
                            if not os.path.exists(python_exe):
                                python_exe = sys.executable
                            
                            if filename.endswith(".py"):
                                exec_cmd = [python_exe, filename]
                                exec_res = subprocess.run(
                                    exec_cmd,
                                    cwd=client.workspace_dir,
                                    capture_output=True,
                                    text=True
                                )
                                if exec_res.returncode == 0:
                                    passed = True
                                    print(f"🎯 [API XÁC THỰC VẬT LÝ] {tc_id}: Chạy thử vật lý thành công!")
                                else:
                                    print(f"❌ [API XÁC THỰC VẬT LÝ] {tc_id}: Chạy thử vật lý thất bại!")
                            else:
                                rel_path = os.path.relpath(target_file_path, client.workspace_dir)
                                comp_res = subprocess.run(
                                    ["javac", rel_path],
                                    cwd=client.workspace_dir,
                                    capture_output=True,
                                    text=True
                                )
                                if comp_res.returncode == 0:
                                    passed = True
                                    print(f"🎯 [API XÁC THỰC VẬT LÝ] {tc_id}: Biên dịch javac CalculatorService thành công!")
                                else:
                                    print(f"❌ [API XÁC THỰC VẬT LÝ] {tc_id}: Biên dịch javac CalculatorService thất bại!")
                        else:
                            if is_finished and "SUCCESS" in final_answer:
                                passed = True

                    results.append({
                        "id": tc_id,
                        "passed": passed,
                        "is_finished": is_finished,
                        "step_count": step_count,
                        "latency": f"{elapsed_time:.2f}s",
                        "final_answer": final_answer,
                        "error": None
                    })

                    # Bắn sự kiện kết quả định lượng của case đó
                    res_data = {
                        'status': 'COMPLETED',
                        'id': tc_id,
                        'passed': passed,
                        'step_count': step_count,
                        'final_answer': final_answer,
                        'latency': f'{elapsed_time:.2f}s'
                    }
                    yield f"data: {json.dumps(res_data, ensure_ascii=False)}\n\n"

                except Exception as e:
                    elapsed_time = time.time() - tc_start_time
                    results.append({
                        "id": tc_id,
                        "passed": False,
                        "is_finished": False,
                        "final_answer": None,
                        "error": str(e)
                    })
                    res_err = {
                        'status': 'COMPLETED',
                        'id': tc_id,
                        'passed': False,
                        'step_count': 0,
                        'final_answer': f'Error: {str(e)}',
                        'latency': f'{elapsed_time:.2f}s'
                    }
                    yield f"data: {json.dumps(res_err, ensure_ascii=False)}\n\n"

            # 4. Bắn sự kiện tổng kết
            total_latency = time.time() - suite_start_time
            passed_count = sum(1 for r in results if r["passed"])
            total_count = len(results)
            pass_rate = (passed_count / total_count) * 100 if total_count > 0 else 0

            summary_payload = {
                "status": "SUMMARY",
                "total_latency": f"{total_latency:.2f}s",
                "passed_count": passed_count,
                "total_count": total_count,
                "pass_rate": f"{pass_rate:.1f}%",
                "results": results
            }
            yield f"data: {json.dumps(summary_payload, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': f'Lỗi hệ thống chạy test suite: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    print("🔥 Khởi động AG2 Orchestrator Server tại cổng 8002...")
    uvicorn.run("services.skill_testing.server:app", host="127.0.0.1", port=8002, reload=True)
