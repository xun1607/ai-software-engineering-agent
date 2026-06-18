# AG2 Orchestrator - Skill Testing Service

Dịch vụ điều phối luồng tư duy và thực thi kỹ năng (Agent Orchestrator) của AI Agent, vận hành dựa trên đồ thị LangGraph và tương tác vật lý ngầm với Hệ điều hành qua môi trường cô lập.

---

## 📋 Điều kiện tiên quyết (Prerequisites)

Để đảm bảo chương trình chạy ổn định và không gặp lỗi import package hay lỗi hiển thị ký tự đặc biệt/emoji trên Windows, bạn cần chuẩn bị:

1. **Virtual Environment (venv):** Sử dụng trình thông dịch Python nằm trong thư mục ảo của dự án:
   * Đường dẫn: `backend/venv/Scripts/python.exe`
2. **Khai báo PYTHONPATH:** Cần thiết lập biến môi trường `PYTHONPATH` trỏ tới thư mục `backend` để Python nhận diện được module `services`.
3. **Bật UTF-8 cho Console (Windows):** Thiết lập biến môi trường `PYTHONUTF8=1` và `PYTHONIOENCODING=utf-8` nhằm tránh lỗi crash hiển thị ký tự tiếng Việt hoặc Emoji (ví dụ: `🚀`, `✅`).
4. **Trạng thái Microservice AG1 (Cổng 8001):**
   * *Nếu AG1 online:* Đồ thị sẽ gọi API thực tế để bốc danh mục kỹ năng động.
   * *Nếu AG1 offline:* Hệ thống sẽ **tự động kích hoạt cơ chế dự phòng (Mock Fallback)** nạp dữ liệu kỹ năng giả lập cục bộ để luồng chạy không bị gián đoạn.

---

## 🚀 Hướng dẫn chạy thử nghiệm

Mở PowerShell tại thư mục `backend/` và chạy các câu lệnh tương ứng dưới đây:

### Lệnh 1: Chạy toàn bộ Test Suite tự động (Khuyên dùng)
Lệnh này sẽ quét qua toàn bộ danh sách kịch bản lỗi trong `testcases.json`, tự động dọn dẹp workspace trước mỗi case, chạy qua đồ thị LangGraph và tổng hợp tỷ lệ Pass/Fail:
```powershell
$env:PYTHONPATH="."; $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe services/skill_testing/run_tests.py
```

### Lệnh 2: Chạy đơn lẻ 1 kịch bản mặc định (Happy Path)
Chạy thử nghiệm một luồng vá lỗi NullPointerException với class Java được mồi sẵn biên dịch thành công:
```powershell
$env:PYTHONPATH="."; $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe services/skill_testing/test_pipeline.py
```

---

## 📁 Cấu trúc thư mục chính liên quan

* `test_pipeline.py`: File chạy đồ thị LangGraph, hiện đã được tham số hóa động để nhận dữ liệu kiểm thử từ bên ngoài.
* `run_tests.py`: Bộ quét chạy test suite tự động, dọn dẹp workspace và thống kê tỷ lệ đạt.
* `testcases.json`: File cấu hình định nghĩa dữ liệu đầu vào cho các ca kiểm thử (gồm happy-path và case lỗi thiếu thư viện).
* `state.py`: Định nghĩa `AgentState` lưu trữ trạng thái đồ thị qua kiểu dữ liệu nguyên thủy (đảm bảo độc lập schema hoàn toàn với AG1).
* `core/skill_client.py`: Trình thực thi vật lý (subprocess.run) quản lý biên dịch và tương tác ổ đĩa thực tế trong thư mục `/workspace`.
* `core/evaluate_node.py`: Node đánh giá chất lượng (QA) kiêm nhiệm thuật toán sinh Stub thông minh khi gặp lỗi biên dịch.

---

## 💡 Các tính năng kiến trúc cốt lõi đã tích hợp

* **Contract Isolation:** Không import chéo bất kỳ class Pydantic nào từ AG1 sang AG2 để đảm bảo tính độc lập tuyệt đối giữa các microservices.
* **Sandbox Execution:** Ép tiến trình biên dịch chạy cố định tại `cwd=workspace_dir` (cô lập trong `backend/workspace/`), cấu hình `capture_output=True` gom sạch `stdout/stderr` cùng bộ ngắt mạch khẩn cấp `timeout=30`.
* **Error-driven Stub Generation:** Khi phát hiện lỗi biên dịch thiếu Class (`cannot find symbol: class User`), hệ thống tự động bẻ luồng ép LLM tạo stub file `User.java` và ghi xuống đĩa cứng để tự phục hồi lỗi biên dịch ở lượt chạy tiếp theo.