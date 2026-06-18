import asyncio
import json
import os
import time
import glob
from services.skill_testing.test_pipeline import run_pipeline
from services.skill_testing.core.skill_client import SkillExecutionClient

async def main():
    # Tải các kịch bản test
    testcases_path = os.path.join(os.path.dirname(__file__), "testcases.json")
    if not os.path.exists(testcases_path):
        print(f"❌ Không tìm thấy file cấu hình tại: {testcases_path}")
        return
    with open(testcases_path, "r", encoding="utf-8") as f:
        testcases = json.load(f)

    # Khởi tạo môi trường
    client = SkillExecutionClient()
    workspace_dir = client.workspace_dir
    java_src_dir = client.java_src_dir

    print(f"📁 Workspace: {workspace_dir}")
    print(f"🧪 Tổng số testcases tìm thấy: {len(testcases)}\n")

    results = []
    suite_start_time = time.time()
    
    for tc in testcases:
        tc_id = tc["id"]
        filename = tc["filename"]
        code_content = tc["code_content"]
        stacktrace = tc["stacktrace"]
        message = tc["message"]

        print("=" * 80)
        print(f"🎬 ĐANG CHẠY TEST CASE: {tc_id}")
        print(f"   Mô tả: {message}")
        print("=" * 80)

        # Làm sạch môi trường
        old_files = glob.glob(os.path.join(java_src_dir, "*.java")) + glob.glob(os.path.join(workspace_dir, "*.py"))
        for fpath in old_files:
            try:
                print(f"🧹 Dọn dẹp tệp tin rác từ case trước: {os.path.basename(fpath)}")
                os.remove(fpath)
            except Exception as e:
                print(f"⚠️ Không thể xóa file {fpath}: {e}")

        tc_start_time = time.time()

        # Chạy pipeline 
        try:
            final_state = await run_pipeline(
                code_content=code_content,
                filename=filename,
                stacktrace=stacktrace,
                message=message
            )
            elapsed_time = time.time() - tc_start_time
            is_finished = False
            final_answer = ""
            step_count = 0
            
            if isinstance(final_state, dict):
                is_finished = final_state.get("is_finished", False)
                final_answer = final_state.get("final_answer", "")
                step_count = final_state.get("step_count", 0)
            else:
                is_finished = getattr(final_state, "is_finished", False)
                final_answer = getattr(final_state, "final_answer", "")
                step_count = getattr(final_state, "step_count", 0)
                
            # Đánh giá kết quả Pass / Fail
            passed = False
            target_file_path = os.path.join(java_src_dir if filename.endswith(".java") else workspace_dir, filename)
            if is_finished and "SUCCESS" in final_answer:
                passed = True
            elif os.path.exists(target_file_path) and os.path.getsize(target_file_path) > 0:
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
            
        except Exception as e:
            elapsed_time = time.time() - tc_start_time
            print(f"❌ Xảy ra ngoại lệ khi chạy test case {tc_id}: {e}")
            results.append({
                "id": tc_id,
                "passed": False,
                "is_finished": False,
                "final_answer": None,
                "error": str(e)
            })

    # Tổng kết
    total_latency = time.time() - suite_start_time
    print("\n" + "=" * 80)
    print("📊 BÁO CÁO TỔNG HỢP TEST SUITE RUNNER")
    print("=" * 80)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    pass_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
    
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        err_msg = f" (Error: {r['error']})" if r["error"] else ""
        print(f"- [{r['id']}] {status} | Finished: {r['is_finished']} | Answer: {r['final_answer']}{err_msg}")
        
    print("-" * 80)
    print(f"📈 TỔNG KẾT SUITE: Tỷ lệ đạt (Pass Rate): {pass_rate:.1f}% ({passed_count}/{total_count})")
    print(f"⏱️ Tổng thời gian quét toàn bộ Testsuite: {total_latency:.2f} giây")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
