# BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC (ARCHITECTURAL DECISION RECORD - ADR)
## ADR-002: Generalized Error-Driven Loop Detection

* **Mã quyết định:** ADR-002
* **Tên quyết định:** Generalized Error-Driven Loop Detection (Phát hiện vòng lặp vô hạn dựa trên chữ ký lỗi chuẩn hóa)
* **Trạng thái:** Đã phê duyệt (Accepted)
* **Tác giả:** AG2 Orchestrator Development Team
* **Ngày tạo:** 2026-06-19

---

### 1. BỐI CẢNH (CONTEXT)

Trong quá trình điều phối luồng tư duy của AI Agent qua đồ thị LangGraph để tự phục hồi lỗi phần mềm (ví dụ: biên dịch mã nguồn Java, chạy mã nguồn Python), hệ thống thường xuyên gặp phải tình trạng lặp vô hạn (Infinite Regression Loop). Điều này xảy ra khi:
1. LLM đề xuất cùng một phương án sửa đổi mã nguồn kém chất lượng (ví dụ: lỗi logic hoặc gõ sai tên phương thức).
2. Trình biên dịch/phiên dịch vật lý trả lại cùng một thông báo lỗi ở lượt chạy tiếp theo.
3. LLM không nhận biết được lịch sử thất bại và tiếp tục áp dụng lại phương án sửa đổi cũ do trôi dạt ngữ cảnh (Context Drift).

Nếu không có cơ chế phát hiện và ngắt mạch tự động, vòng lặp này sẽ tiếp diễn cho đến khi vượt quá giới hạn bước cứng (Circuit Breaker) hoặc làm cạn kiệt chi phí API (Token Cost) của hệ thống. Đồng thời, việc truyền toàn bộ nội dung thô của stacktrace lỗi vào ngữ cảnh đánh giá gây ra lãng phí tài nguyên và làm nhiễu khả năng suy luận của LLM.

---

### 2. QUYẾT ĐỊNH KIẾN TRÚC (DECISION)

Chúng tôi quyết định triển khai thuật toán **Phát hiện vòng lặp dựa trên chữ ký lỗi chuẩn hóa và ngắt đồ thị an toàn (Generalized Error-Driven Loop Detection)** tại Node Đánh giá (`evaluate_node`). Chi tiết giải pháp kỹ thuật bao gồm:

#### 2.1 Chuẩn hóa lỗi bằng Regex (Normalized Error Signature)
Hệ thống sẽ lọc bỏ các chi tiết động (như địa chỉ bộ nhớ, dấu thời gian, số dòng thay đổi) và gom cụm thông báo lỗi vật lý từ `stdout/stderr` thành các nhãn chữ ký tĩnh bằng Regex:
* **Java NullPointerException:** Khớp `NullPointerException`.
* **Python Module/Import Error:** Khớp `ModuleNotFoundError` hoặc `ImportError` và trích xuất chính xác tên thư viện bị thiếu (ví dụ: `ModuleNotFoundError: requests`).
* **Java Symbol/Compilation Error:** Khớp `cannot find symbol` và bóc tách thực thể bị thiếu (Class, Method, Variable).
* **Arithmetic Error:** Khớp `ArithmeticException` (ví dụ: chia cho 0).
* **File Error:** Khớp `FileNotFoundError`.
* **Fallback an toàn:** Nếu quan sát có trạng thái lỗi (`status == "FAILED"`) hoặc chứa từ khoá liên quan đến ngoại lệ nhưng không khớp Regex nào, hệ thống tự động gán nhãn `"GENERIC_ERROR"` để phòng ngừa crash.

#### 2.2 Vân tay thực thi (Execution Fingerprint)
Tại mỗi bước đánh giá, hệ thống sẽ trích xuất một bộ vân tay 3 thành phần (Tuple):
$$\text{Fingerprint} = (\text{Current Task}, \text{Selected Skill}, \text{Normalized Error Signature})$$
Bộ vân tay này được lưu lũy tiến vào thuộc tính `fingerprint_history` của `AgentState`.

#### 2.3 Cơ chế ngắt mạch vòng lặp (Safe Terminate Loop Detector)
Trước khi đưa ra quyết định rẽ nhánh đồ thị, hệ thống sẽ so sánh các vân tay trong lịch sử:
* Nếu **3 vân tay thực thi liên tiếp hoàn toàn trùng nhau**, đồ thị sẽ kích hoạt ngắt mạch ngay lập tức.
* Hệ thống thiết lập thuộc tính `state.need_replan = True`, `state.is_finished = True` và đặt kết quả cuối cùng (`state.final_answer`) chứa thông báo mô tả lỗi kèm chi tiết vân tay gây lặp.
* Đồ thị được định hướng kết thúc an toàn tại điểm ngắt `END`, giải phóng tài nguyên hệ thống.

---

### 3. HẬU QUẢ & ẢNH HƯỞNG (CONSEQUENCES)

#### 3.1 Ưu điểm (Consequences - Positive)
* **Bảo vệ Tài chính (Cost Protection):** Ngăn chặn 100% tình trạng cạn kiệt tài khoản API Key khi LLM bị kẹt trong vòng lặp thử sửa lỗi không thành công.
* **Tối thiểu hóa Latency:** Kết thúc tiến trình lỗi deterministic sau tối đa 3 vòng lặp thay vì chờ hết giới hạn bước cứng (ví dụ: 12 hoặc 20 bước).
* **Decoupled Architecture:** Sử dụng kiểu dữ liệu nguyên thủy (Primitive tuples, strings) để lưu trữ vân tay, giữ cho `AgentState` tương thích hoàn toàn với các giao thức Serialization (JSON, gRPC) của Microservices.

#### 3.2 Nhược điểm (Consequences - Negative)
* **Độ chính xác Regex:** Cơ chế chuẩn hóa phụ thuộc vào bộ mẫu Regex định nghĩa sẵn. Nếu gặp các framework hoặc ngôn ngữ lập trình mới, chữ ký có thể bị phân loại nhầm thành `"GENERIC_ERROR"`. Tuy nhiên, cơ chế fallback vẫn đảm bảo Loop Detector hoạt động chính xác vì vân tay vẫn sẽ trùng khớp nhãn `"GENERIC_ERROR"`.
* **Thiếu khả năng tự sửa lỗi động trong vòng lặp (Static Terminate):** Việc ngắt đồ thị cứng ở bước này buộc ứng dụng gọi API phía ngoài phải thực hiện tái lập kế hoạch vĩ mô thay vì tự động chuyển hướng skill ngay lập tức. (Vấn đề này sẽ được giải quyết ở Sprint tiếp theo bằng cơ chế *Adaptive Replanning*).
