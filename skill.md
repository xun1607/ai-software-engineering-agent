---
# --------------- Metadata

name: debug-java-null-pointer
description: Dùng để xác định nguyên nhân và dòng code gây lỗi   NullPointerException trong dự án Java.
version: 1.0.0

# Taxonomy (Epic 2)
category: SoftwareEngineering/Debugging   # Dùng để phân loại
level: composite  # Hoặc "atomic" nếu nó không gọi các skill khác
tags: [java, backend, troubleshooting]

# Interface Definition (Epic 1 & 4 - Cực kỳ quan trọng để nối skill)
# Tức là input và output có dạng json với các properties tương ứng, required là yêu cầu properties đó tồn tại
input:
  type: object
  required: [stacktrace, source_path]
  properties:
    stacktrace: { type: string, description: "Toàn bộ log lỗi" }
    source_path: { type: string, description: "Đường dẫn root của source code" }

output:
  type: object
  properties:
    file: { type: string }
    line: { type: integer }
    fix_suggestion: { type: string }

# Điều kiện thực thi
constraints:
  # 1. Host Environment (Những gì máy thực thi phải có)
  host:
    binaries: ["grep", "find", "psql"]           # Tool dòng lệnh
    runtimes:                                    # Môi trường chạy code
      - { name: "java", version: ">=17" }
      - { name: "python", version: ">=3.9" }
    os: ["linux", "darwin"]                      # Hệ điều hành hỗ trợ

  # 2. Resource Limits (Giới hạn tài nguyên - Tránh treo máy)
  resources:
    memory: "2GB"
    cpu_cores: 2
    timeout: "60s"                               # Chạy quá lâu là tự kill
    network: "restricted"                        # internal_only, none, or full

  # 3. Security & Safety (Quyền hạn và an toàn)
  safety:
    fs_access: "read-only"                       # read-only, write-protected, full
    db_access: "select-only"                     # Quyền với database
    requires_approval: true                      # Có cần con người bấm "Yes" mới chạy không?
---

# 🛠 Debug Java Null Pointer (Phần dành cho Người & Agent đọc - Epic 1)

## 📋 Goal
Xác định chính xác vị trí biến bị null và đề xuất phương án khởi tạo hoặc check null hợp lý.

## 🚀 Instructions
1. **Phân tích Stacktrace:** Tìm dòng đầu tiên có chứa package của dự án (loại bỏ các thư viện bên thứ 3).
2. **Truy vết Code:** Mở file tại dòng đã xác định, kiểm tra các biến tham chiếu trong dòng đó.
3. **Kiểm tra Logic:** Xem xét các điểm khởi tạo biến (constructor, dependency injection).

## Example
...



## ⚠️ Common Mistakes
- Nhầm lẫn giữa lỗi NullPointer của logic nghiệp vụ và lỗi của framework (như Spring).
- Quên không kiểm tra các file cấu trúc như `pom.xml` hay `application.properties`.

## 🔗 Related Skills (Epic 4 - Composition)
- [[fix-java-code]] - Sau khi tìm ra root cause, dùng skill này để sửa.
- [[run-unit-test]] - Sau khi sửa xong, dùng skill này để verify.