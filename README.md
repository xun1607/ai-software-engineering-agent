# AI Software Engineering Agent Platform

Hệ thống microservice quản lý, đánh giá và thực thi Skill cho AI Agent. Hệ thống cho phép quản lý vòng đời của các kỹ năng (Skills) từ lúc khởi tạo, đánh giá chất lượng đến việc nạp vào Agent để thực thi các tác vụ SWE tự động.

## 🚀 Tính năng nổi bật

- **Centralized Skill Registry**: Quản lý Skill tập trung trong Database, đồng bộ hóa tự động từ thư mục `skill_library`.
- **Autonomous Agent Chat**: Giao diện Chatbot thông minh sử dụng **LangGraph**. Agent có khả năng tự lập kế hoạch, phát hiện các kĩ năng cần thiết (Tool Discovery) và thực thi chúng để giải quyết task.
- **Multi-Model Support**: Hỗ trợ linh hoạt các Model từ DeepSeek (V3, R1) đến OpenAI (GPT-4o).
- **Automated Evaluation**: Hệ thống đánh giá tự động điểm số tài liệu (Doc Score) và tỷ lệ vượt qua test case (Pass Rate).
- **Modern UI**: Giao diện Dark mode hiện đại, hỗ trợ render Markdown chuyên nghiệp với Syntax Highlighting.

## 🏗️ Kiến trúc Hệ thống

Hệ thống bao gồm 4 microservices chính:

- **skill-management (Port 8001)**: CRUD skill, cung cấp Tool Definition chuẩn LangChain/LangGraph.
- **skill-evaluation (Port 8002)**: Đánh giá chất lượng tài liệu và chạy kiểm thử tự động.
- **skill-testing (Port 8003)**: Môi trường Agent Chat và thực thi Skill thực tế.
- **skill-reporting (Port 8004)**: Dashboard thống kê và báo cáo tổng hợp.

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

Sau khi khởi chạy:
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8001/docs`

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
