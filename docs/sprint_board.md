# BẢNG NHIỆM VỤ SPRINT & ĐỊNH NGHĨA HOÀN THÀNH (DoD)
## Sprint: Benchmark Framework & Evaluation Suite

Hồ sơ theo dõi tiến độ các đầu việc phát triển khung thử nghiệm và đánh giá chất lượng Agent.

---

### 1. BẢNG NHIỆM VỤ (TASK BOARD)

#### 🟩 CỘT HOÀN THÀNH (DONE)
*   **`[TASK_DESIGN]` (Thiết kế Kiến trúc Benchmark):** Phác thảo thiết kế cấu trúc thư mục, định nghĩa các lược đồ `testcase.json`, `expected.json`, và `benchmark_results.json` phiên bản nghiên cứu học thuật; đề xuất 8 kịch bản lỗi từ Spring PetClinic.

#### 🟦 CỘT ĐANG THỰC HIỆN (IN PROGRESS)
*   *Hiện tại không có tác vụ nào đang code (chỉ ở bước thiết kế).*

#### 🟨 CỘT CHỜ TRIỂN KHAI (BACKLOG) - PHÂN CHIA SPRINT MỚI

##### Nhóm P0: Hạ tầng cốt lõi & Dữ liệu Testcases (Phải làm ngay)
*   **`[TASK_P0_1]` (Workspace Isolation Manager):** Hiện thực hóa module tự động clone/copy từ `benchmark_repos/` sang một thư mục workspace tạm (`workspace_temp/`) để cô lập môi trường chạy thử và rollback git sau mỗi run.
*   **`[TASK_P0_2]` (Automated Bug Injector):** Viết module đọc cấu hình `bug_injection` từ `testcase.json` và tiêm lỗi (thay thế dòng hoặc áp dụng patch) vào file nguồn vật lý tương ứng.
*   **`[TASK_P0_3]` (Spring PetClinic Testcases Setup):** Hiện thực hóa thư mục dữ liệu cho 8 testcases Spring PetClinic (từ NPE dễ đến Circular Dependency phức tạp) bao gồm `testcase.json`, `expected.json`, và `patch.diff` chuẩn.

##### Nhóm P1: Bộ điều phối so sánh & Trình chạy đối chứng (Phải làm ngay)
*   **`[TASK_P1_1]` (Baseline Runners):** Thiết lập module chạy cho Baseline A (Pure LLM - prompt trực tiếp sửa đổi) và Baseline B (Top-1 Similarity - tự động chọn và tham số hóa 1 kỹ năng).
*   **`[TASK_P1_2]` (run_comparison.py Orchestrator):** Viết script so sánh trung tâm, điều phối chạy tuần tự các testcases qua 3 chế độ (Baseline A, Baseline B, CASS Orchestrator), thu thập telemetry và khôi phục môi trường.
*   **`[TASK_P1_3]` (Telemetry & Exporter):** Xây dựng module thu thập số liệu chi tiết (độ trễ ms, chi phí USD, tokens) từ `node_trace` và xuất kết quả ra `benchmark_results.json` theo định dạng số thực.

##### Nhóm P2: Giao diện trực quan & Tích hợp sâu (Trì hoãn)
*   **`[TASK_P2_1]` (React Dashboard):** Xây dựng trang quản lý và biểu diễn trực quan (bảng so sánh, biểu đồ hình cột so sánh Pass Rate, Latency, Cost) trong giao diện frontend của dự án.
*   **`[TASK_P2_2]` (Maven Offline Cache Optimization):** Tinh chỉnh cấu hình Maven trong sandbox sử dụng offline cache hoặc chia sẻ `.m2/repository` để giảm thời gian build từ ~15s xuống <3s.

---

### 2. ĐỊNH NGHĨA HOÀN THÀNH (DEFINITION OF DONE - DoD)

Mọi mã nguồn và cấu hình được đưa vào nhánh chính trong Sprint này bắt buộc phải tuân thủ nghiêm ngặt các quy tắc DoD dưới đây:

*   **`[DoD_1] Primitive Data Isolation`:** Các state của Agent và dữ liệu trả về của testcase/expected/results tuyệt đối không chứa đối tượng Class/Object phức tạp. Chỉ sử dụng kiểu dữ liệu nguyên thủy (`str`, `int`, `float`, `list`, `dict`) để phục vụ serialization phi tập trung.
*   **`[DoD_2] Numeric Metric Integrity`:** Tất cả các chỉ số hiệu năng (Latency, Token, Cost) bắt buộc phải lưu dưới dạng số (`int` cho milliseconds và tokens, `float` cho USD) thay vì dạng chuỗi (không dùng `"5.1s"`, `"1200 tokens"`).
*   **`[DoD_3] Sandbox Integrity & Recovery`:** Trình chạy testcase phải đảm bảo phục hồi trạng thái git sạch (`git reset --hard` và `git clean -fd`) sau mỗi lần thực thi một chế độ agent để tránh ô nhiễm mã nguồn.
*   **`[DoD_4] No Hardcoded Pass`:** Kết quả đánh giá PASSED của testcase phải được chứng minh thực tế bằng cách chạy biên dịch thật (`exit code 0` của lệnh build) và chạy unit tests thật, không được giả lập kết quả.
