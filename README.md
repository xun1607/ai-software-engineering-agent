# AG2: Context-Aware Skill Selection Framework (CASS Framework) for AI Software Engineering Agents

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/LangGraph-0.2.14-orange.svg)](https://github.com/langchain-ai/langgraph)
[![LLM API](https://img.shields.io/badge/OpenAI-gpt--4o-green.svg)](https://platform.openai.com/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

Báo cáo & Mã nguồn Đồ án Học phần **Nghiên cứu tốt nghiệp 1 (GR1)**  
**Đề tài AG2**: *Kết hợp và điều phối các AI Agent Skills trong Software Engineering theo ngữ cảnh (Context-Aware Skill Selection Framework --- CASS Framework)*  

- **Sinh viên thực hiện**: Nguyễn Minh Xuân (MSSV: `20235882`)  
- **Email**: `xuan.nm235882@sis.hust.edu.vn`  
- **Giảng viên hướng dẫn**: TS. Vũ Thị Hương Giang  
- **Khoa**: Khoa học Máy tính  
- **Trường**: Công nghệ thông tin và Truyền thông - Đại học Bách khoa Hà Nội  

---

## 🎯 GIỚI THIỆU CHUNG VÀ ĐẶT VẤN ĐỀ

Các AI Software Engineer Agent (SWE-Agent) hiện đại ngày càng phụ thuộc vào danh mục công cụ/kỹ năng (*Agent Skills*) phong phú để tự động hóa quy trình sửa lỗi phần mềm. Tuy nhiên, việc mở rộng thư viện kỹ năng dẫn tới 3 thách thức kỹ thuật cốt lõi:

1. **Hiện tượng Skill Bloat (Phình to Ngữ cảnh)**: Nạp 40+ kỹ năng vào System Prompt làm dung lượng token vọt lên $>5,000$ tokens/run, gây lãng phí chi phí tài chính API ($0.014+/run$) và làm mô hình suy luận kém chính xác.
2. **Xung đột Môi trường Thực thi (Host Execution Conflicts)**: Agent gọi các lệnh Linux thô (như `grep`, `bash`) trên máy chủ Windows dẫn tới sụp đổ tiến trình với Tỷ lệ Crash Rate lên tới 18.0%.
3. **Lựa chọn Ngẫu nhiên Thiếu Uy tín (Unreliable RAG Selection)**: Các cơ chế RAG tĩnh chỉ dựa vào mô tả từ ngữ mà không đánh giá được độ ổn định và tỷ lệ thành công thực tế của công cụ qua các lần thực thi.

**CASS Framework (Context-Aware Skill Selection)** được đề xuất như một Khung điều phối độc lập nền tảng (*Framework-Agnostic*), đóng vai trò là "Bộ não Quản lý Uy tín" giúp gạt bỏ sớm công cụ không tương thích, tự động lọc và xếp hạng kỹ năng theo ngữ cảnh nhiệm vụ và môi trường máy host thời gian thực.

---

## 💡 MỤC TIÊU VÀ PHƯƠNG PHÁP LUẬN CASS

### 1. Đường ống Lọc Đa tầng (Multi-tier Filtering Pipeline)
- **Tầng 1 --- Lọc Ràng buộc Môi trường ($\mathcal{O}(N)$)**: Lọc cứng các thuộc tính môi trường máy host (`sys.platform` và RAM). Loại bỏ ngay các công cụ không hỗ trợ OS hiện tại.
- **Tầng 2 --- Lọc Tương đồng Ngữ nghĩa ($\mathcal{O}(N \cdot D)$)**: Trích xuất Vector nhúng Cosine Similarity $\mathrm{Sim}(s, u_i)$ giữa Subtask $u_i$ và mô tả kỹ năng $s$, thu hẹp danh sách ứng viên liên quan.
- **Tầng 3 --- Xếp hạng Bayesian Thompson Sampling ($\mathcal{O}(N \log N)$)**: Rút mẫu ngẫu nhiên từ Phân phối xác suất Beta $\mathrm{Beta}(\alpha, \beta)$ để tự động cân bằng giữa việc *Khai thác* kỹ năng tin cậy và *Khám phá* kỹ năng mới.

### 2. Mô hình Uy tín Xác suất Beta và Hàm Utility Score
Độ tin cậy của mỗi kỹ năng được lưu vết trong CSDL SQLite qua bộ tham số $(\alpha, \beta)$:
$$E[\theta_s] = \frac{\alpha_s}{\alpha_s + \beta_s} \quad \text{với } \alpha \leftarrow \alpha + 1 \text{ (nếu PASS)}, \, \beta \leftarrow \beta + 1 \text{ (nếu FAIL)}$$

Điểm xếp hạng tổng hợp CASS được tính toán qua hàm Utility Score Đa mục tiêu:
$$\mathrm{Score}(s) = \mathrm{Sim}(s, u_i) \times \widetilde{\theta}_s - \left(w_{\text{latency}} \cdot \text{NormLatency}_s\right)$$

---

## 📊 KẾT QUẢ THỰC NGHIỆM ĐỊNH LƯỢNG

Phân tích 66 lượt chạy thực nghiệm đối chứng trên 12 bộ bài testcases (từ bài test cú pháp Python/Java đến các bài toán thực tế thuộc bộ dữ liệu **SWE-bench Lite** như Pallets Flask, Requests, Astropy) ghi nhận:

| Chỉ số Đánh giá (Metric) | Baseline (Không lọc) | CASS-Enabled | Mức độ Cải thiện |
| :--- | :---: | :---: | :---: |
| **Dung lượng Prompt Tokens (Avg)** | 5,199 tokens | **1,644 tokens** | 📉 **Cắt giảm 72.1%** |
| **Chi phí API Trung bình (USD)** | $0.0142 / run | **$0.0045 / run** | 💰 **Tiết kiệm 68.3%** |
| **Thời gian Phản hồi Latency (ms)** | 7,441 ms | **4,335 ms** | ⚡ **Rút ngắn 46.0% (1.7x)** |
| **Tỷ lệ Crash do xung đột OS** | 18.0% | **0.0%** | 🛡️ **Triệt tiêu 100% Crash** |
| **Tỷ lệ Thành công Tổng thể** | 82.0% | **92.0%** | 🎯 **Nâng Tỷ lệ Thành công** |

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG (TECH STACK)

| Công cụ / Thư viện | Phiên bản | Vai trò trong Hệ thống | Giấy phép |
| :--- | :---: | :--- | :---: |
| **Python** | `3.10.11` | Ngôn ngữ lập trình trung tâm | PSF |
| **LangGraph** | `0.2.14` | Khung đồ thị trạng thái Agent (3 Nút Reasoning, Action, Verify) | MIT |
| **OpenAI SDK** | `1.35.13` | Giao tiếp mô hình LLM Brain (`gpt-4o`) | MIT |
| **SQLite** | `3.42.0` | CSDL nhúng quản lý Uy tín Bayesian $(\alpha, \beta)$ | Public Domain |
| **NumPy & SciPy** | `1.26.4` / `1.13.1` | Tính toán Cosine Similarity & Phân phối Beta PDF | BSD 3-Clause |
| **pytest** | `8.2.2` | Công cụ kiểm thử nghiệm thu tự động trong Sandbox | MIT |
| **Streamlit** | `1.36.0` | Framework Giao diện Control Center Dashboard 4 Khu vực | Apache 2.0 |

---

## 📂 CẤU TRÚC MÃ NGUỒN DỰ ÁN

```text
ai-software-engineering-agent/
├── backend/
│   └── services/
│       └── skill_testing/
│           ├── cass/                        # Phân hệ Điều phối CASS Framework
│           │   ├── core.py                  # Core Orchestration Pipeline
│           │   ├── filter/                  # Constraint & Semantic Filters
│           │   ├── ranker/                  # Thompson Sampling & Utility Ranker
│           │   └── storage/                 # SQLite DB Manager Interface
│           │
│           ├── swe_agent/                   # Phân hệ SWE-Agent thực thi (LangGraph)
│           │   ├── core/                    # LLM Brain & LocalSandbox Engine
│           │   ├── skills/                  # Dynamic SKILL.md Registry & Telemetry Proxy
│           │   └── workflow/                # LangGraph 3-Node Workflow (Reasoning, Action, Verify)
│           │
│           ├── skills/                      # Thư viện 40 Agent Skills (SKILL.md)
│           ├── benchmark_repos/             # Mã nguồn lỗi các kịch bản testcase
│           ├── app_dashboard.py             # CASS Control Center Dashboard (Streamlit 4-Zone UI)
│           ├── benchmark_cass.py            # Tool Benchmark Tự động Batch Runner
│           ├── extract_swe_lite.py          # Converter trích xuất SWE-bench Lite
│           ├── export_test_report.py        # Script xuất báo cáo TEST_REPORT.md / TEST_REPORT.csv
│           ├── benchmark_cass.db            # Cơ sở dữ liệu Uy tín SQLite (Beta PDF)
│           ├── benchmark_results.csv        # Nhật ký thực nghiệm thô 66 Runs
│           ├── TEST_REPORT.md               # Báo cáo Kiểm thử Thực nghiệm (Mục R.4.1)
│           ├── DEFENSE_SLIDES_GUIDE.md      # Dàn ý & Lời thoại Slide Bảo vệ Đồ án
│           ├── VIDEO_DEMO_AND_PRESENTATION_SCRIPT.md # Kịch bản chi tiết quay Video Demo
│           └── requirements.txt             # Danh mục thư viện phụ thuộc
├── .gitignore                               # Cấu hình bỏ qua tệp tạm & API key
└── README.md                                # Hướng dẫn dự án chính
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT VÀ KHỞI CHẠY HỆ THỐNG

### 1. Yêu cầu Môi trường
- **Python**: `3.10` trở lên
- **Hệ điều hành**: Windows / Linux / macOS

### 2. Khởi tạo Môi trường ảo và Cài đặt Phụ thuộc
Mở terminal tại thư mục gốc dự án và thực hiện:

```bash
# Tạo môi trường ảo 
python -m venv venv

# Kích hoạt môi trường ảo (Windows)
.\venv\Scripts\activate

# Cài đặt phụ thuộc từ skill_testing
pip install -r backend/services/skill_testing/requirements.txt
```

### 3. Cấu hình OpenAI API Key
Tạo tệp `.env` tại thư mục `backend/services/skill_testing/.env`:

```env
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
```

### 4. Khởi chạy CASS Control Center Dashboard (Streamlit UI)
Chạy lệnh sau để khởi động Giao diện Điều khiển 4 Khu vực:

```bash
cd backend/services/skill_testing
streamlit run app_dashboard.py
```

Trình duyệt sẽ tự động mở giao diện tại địa chỉ: **`http://localhost:8501`**.

---

## 🧪 CHẠY THỬ NGHIỆM 

### Chạy Benchmark Tự động Batch Runner
Chạy lệnh bên dưới để thực thi đối chứng giữa **Baseline** và **CASS-Enabled**:

```bash
cd backend/services/skill_testing
python benchmark_cass.py --runs 2
```

