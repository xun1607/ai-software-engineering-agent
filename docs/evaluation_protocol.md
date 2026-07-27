# Giao thức Đánh giá Hiệu năng (Evaluation Protocol)
Tài liệu này định nghĩa cơ sở toán học và quy chuẩn đo lường hiệu năng của AI Agent trong việc lựa chọn và thực thi Kỹ năng.

---

## 1. Định lượng Chất lượng Đầu ra (Output Quality)
Chất lượng đầu ra ($Q$) được biểu diễn dưới dạng số thực liên tục $Q \in [0, 1]$, được đo lường tự động qua các tác vụ:

### 1.1. Sửa lỗi lập trình (Bug Fixing)
Chất lượng dựa trên tỷ lệ vượt qua các ca kiểm thử đơn vị vật lý (Unit Tests):
$$Q_{\text{bug}} = \frac{N_{\text{passed}}}{N_{\text{total}}}$$
*   Trong đó: $N_{\text{passed}}$ là số lượng testcase biên dịch và chạy thành công; $N_{\text{total}}$ là tổng số testcase kiểm thử của task.

### 1.2. Sinh mã kiểm thử (Unit Test Generation)
Chất lượng đo lường bằng độ bao phủ mã nguồn (Branch Coverage) được sinh ra:
$$Q_{\text{test}} = \text{Branch Coverage Score} \in [0, 1]$$
*   Đo lường thông qua công cụ phân tích độ bao phủ vật lý (như JaCoCo cho Java hoặc Coverage.py cho Python).

### 1.3. Giải thích mã nguồn (Code Explanation)
Đo lường độ tương đồng ngữ nghĩa (Cosine Similarity) giữa câu trả lời của Agent và tài liệu chuẩn (Ground Truth):
$$Q_{\text{explain}} = \cos(\mathbf{v}_{\text{agent}}, \mathbf{v}_{\text{truth}}) = \frac{\mathbf{v}_{\text{agent}} \cdot \mathbf{v}_{\text{truth}}}{\|\mathbf{v}_{\text{agent}}\| \|\mathbf{v}_{\text{truth}}\|}$$
*   Sử dụng mô hình SentenceTransformer để chuyển đổi văn bản giải thích thành vector $\mathbf{v}$.

### 1.4. Đánh giá mã nguồn (Code Review)
Đo lường tỷ lệ bao phủ lỗi bảo mật/logic phát hiện được (Recall):
$$Q_{\text{review}} = \frac{D_{\text{detected}}}{D_{\text{actual}}}$$
*   Trong đó: $D_{\text{detected}}$ là số lượng lỗi thật sự được Agent chỉ ra; $D_{\text{actual}}$ là tổng số lỗi được gài sẵn trong mã nguồn.

---

## 2. Điểm tham chiếu (Reference Point) cho Hypervolume
Hypervolume (HV) đo thể tích không gian bị bao phủ bởi giải pháp tối ưu so với một điểm tệ nhất (Reference Point). Điểm tham chiếu được cố định dựa trên dữ liệu tệ nhất quan sát được trên tập huấn luyện nhân với hệ số an toàn $1.2$:

$$r_1 (\text{failure\_rate}) = 1.2 \times \max(1 - \text{TSR})$$
$$r_2 (\text{normalized\_cost}) = 1.2 \times \max(\text{NormalizedCost})$$
$$r_3 (\text{normalized\_latency}) = 1.2 \times \max(\text{NormalizedLatency})$$

*   **Chính sách thực nghiệm:** Sau khi tính toán từ dữ liệu chạy thử đầu tiên, điểm tham chiếu $R = (r_1, r_2, r_3)$ sẽ được **đóng băng (freeze)** và áp dụng chung cho tất cả các Baseline.

---

## 3. Tính toán Hypervolume 3D Hệ thống (System-level HV)
Sau khi kết thúc toàn bộ tập kiểm thử (Test Set), hiệu năng của một Baseline được quy về một điểm $Y = (y_1, y_2, y_3)$ trong không gian tối thiểu hóa (minimization space):
1.  $y_1 = 1 - \text{TSR}$ (Tỷ lệ tác vụ thất bại)
2.  $y_2 = \text{Average Cost chuẩn hóa} = \text{AvgCost} / \max(\text{Cost})$
3.  $y_3 = \text{Average Latency chuẩn hóa} = \text{AvgLatency} / \max(\text{Latency})$

Thể tích Hypervolume bị bao phủ bởi giải pháp $Y$ so với điểm tham chiếu $R$ được tính bằng:
$$\text{HV}(Y) = (r_1 - y_1) \times (r_2 - y_2) \times (r_3 - y_3)$$

*   *Ý nghĩa:* Giá trị $\text{HV}(Y)$ càng lớn chứng tỏ phương pháp càng đạt độ cân bằng (Trade-off) tốt giữa độ chính xác và chi phí tài nguyên.

---

## 4. Đo lường Độ đóng khoảng cách (Gap Closure)
Để lượng hóa khả năng tối ưu hóa của Framework so với giải pháp cơ sở tốt nhất (SBS) và giới hạn lý thuyết tối đa (VBS - Oracle), chỉ số Gap Closure được tính bằng:

$$\text{Gap Closure} = \frac{\text{HV}(\text{Proposed}) - \text{HV}(\text{SBS})}{\text{HV}(\text{VBS}) - \text{HV}(\text{SBS})} \times 100\%$$

*   **SBS (Single Best Solver):** Chọn duy nhất một skill có hiệu năng trung bình tốt nhất trên tập train để áp dụng cho mọi task trên tập test.
*   **VBS (Virtual Best Solver):** Giả định một bộ chọn lọc hoàn hảo (Oracle) luôn biết trước và chọn trúng skill tốt nhất cho từng task cụ thể.
