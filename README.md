# AI Software Engineering Agent Platform

Hệ thống microservice quản lý, đánh giá và thực thi Skill cho AI Agent. Hệ thống cho phép quản lý vòng đời của các kỹ năng (Skills) từ lúc khởi tạo, đánh giá chất lượng đến việc nạp vào Agent để thực thi các tác vụ SWE tự động.

## 🚀 Tính năng nổi bật

- **Centralized Skill Registry**: Quản lý Skill tập trung trong Database, đồng bộ hóa tự động từ thư mục `skill_library`.
- **Autonomous Agent Chat**: Giao diện Chatbot thông minh sử dụng **LangGraph**. Agent có khả năng tự lập kế hoạch, phát hiện các kĩ năng cần thiết (Tool Discovery) và thực thi chúng để giải quyết task.
- **Multi-Model Support**: Hỗ trợ linh hoạt các Model từ DeepSeek (V3, R1) đến OpenAI (GPT-4o).
- **Automated Evaluation**: Hệ thống đánh giá tự động điểm số tài liệu (Doc Score) và tỷ lệ vượt qua test case (Pass Rate).
- **Modern UI**: Giao diện Dark mode hiện đại, hỗ trợ render Markdown chuyên nghiệp với Syntax Highlighting.

## 🏗️ Kiến trúc Hệ thống

Hệ thống bao gồm các thành phần microservices phối hợp:

- **skill-management (Port 8001)**: CRUD skill, cung cấp Tool Definition chuẩn LangChain/LangGraph.
- **skill-evaluation (Port 8002)**: Đánh giá chất lượng tài liệu và chạy kiểm thử tự động.
- **skill-testing (Port 8003)**: Môi trường Agent Chat và thực thi Skill thực tế.
- **skill-reporting (Port 8004)**: Dashboard thống kê và báo cáo tổng hợp.

- ### 🧠 Core Orchestrator Service (Bộ não điều phối AI - AG2)
- **skill-agent-ag2 (Port 8000)**: Engine cốt lõi chịu trách nhiệm vận hành Agentic Workflow dựa trên **LangGraph State Graph**. 
  - **2-Stage Skill Routing**: Cơ chế lọc kĩ năng 2 tầng tối ưu token. Tầng 1 sử dụng Vector Embedding cục bộ qua mô hình `all-MiniLM-L6-v2` để tính điểm cosine similarity sàng lọc ứng viên. Tầng 2 dùng LLM để ánh xạ chính xác và bốc trích đối số (Arguments Extraction) dưới dạng JSON nghiêm ngặt.
  - **Dynamic Re-planning & Self-Correction**: Tự động phát hiện lỗi thực thi mã nguồn, kích hoạt vòng lặp Retry (tối đa 2 lần) hoặc tái lập kế hoạch (Re-plan) linh hoạt khi Node đánh giá (Evaluate) gửi tín hiệu lỗi.
  - **Real-time SSE Streaming**: Stream dữ liệu trạng thái xử lý từng Node (`Planning`, `Selector`, `Execution`, `Evaluate`) theo thời gian thực về UI React thông qua giao thức Server-Sent Events (SSE).

## 🛠️ Cài đặt và Khởi chạy

### Sử dụng Docker Compose (Khuyên dùng)

Hệ thống được container hóa hoàn toàn, bao gồm cả Database PostgreSQL.

```bash
# Clone project
git clone https://github.com/xun1607/ai-software-engineering-agent
cd ai-software-engineering-agent

# Khởi chạy toàn bộ hệ thống
docker compose up --build -d
```
### Cấu hình biến môi trường
Tạo file `.env` nằm ngay tại thư mục gốc của dự án (nơi chứa file `docker-compose.yml`) và bổ sung API Key của bạn:
`OPENAI_API_KEY=sk-your-actual-openai-key-here`

### Sau khi khởi chạy:
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8001/docs`

Lưu ý: Lần build đầu tiên của service skill-agent-ag2 sẽ mất từ 1-2 phút do hệ thống tự động tải và đóng gói cấu phần mô hình Embedding all-MiniLM-L6-v2 tối ưu hóa cho CPU nhằm chạy offline bộ lọc ngữ nghĩa tầng 1.

### Khởi chạy thủ công độc lập cho AG2 (Môi trường phát triển/Dự phòng)
Nếu muốn debug riêng lẻ mã nguồn điều phối Agent không qua Docker, bạn có thể chạy trực tiếp bằng môi trường ảo Python local:
```
cd backend/services/ag2

# Kích hoạt môi trường ảo (Windows)
.\venv\Scripts\activate

# Khởi chạy API Server với tính năng hot-reload
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
## 📝 Định dạng Skill (SKILL.md)

Mỗi Skill được định nghĩa bằng định dạng Markdown kèm YAML Frontmatter:

```md
---
name: "debug_python"
version: "1.0.0"
category: "python"
level: "composite"
tags: ["debugging", "testing"]
description: "Sử dụng để tìm và sửa lỗi trong mã nguồn Python"
---

## 🚀 Instructions
Nội dung hướng dẫn chi tiết cho Agent về cách sử dụng skill này...

## 🧪 Test Cases
Các trường hợp kiểm thử để đánh giá hiệu quả của skill.
```

## 🤖 Agent Chat Usage

1. Truy cập vào mục **Testing** trên giao diện Web.
2. Mở bảng **Settings** để chọn Model (DeepSeek/OpenAI) và điền API Key.
3. Nhập yêu cầu, ví dụ: `"Fix bug in file /app/buggy_code.py"`.
4. Agent sẽ tự động:
   - Phân tích yêu cầu.
   - Tìm kiếm kĩ năng phù hợp trong Registry.
   - Lập kế hoạch và thực thi kĩ năng để hoàn thành task.

---
Phát triển bởi **Antigravity Team**.
