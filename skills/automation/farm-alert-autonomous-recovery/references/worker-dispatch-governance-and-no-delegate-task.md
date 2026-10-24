# Worker Dispatch Governance & Prohibition of Hermes Subagents (`delegate_task`)

## 1. Core Rule: Hard Ban on `delegate_task`
- **CẤM TUYỆT ĐỐI**: Coordinator không được phép gọi `delegate_task` (Hermes native subagent).
- **Lý do**:
  1. `delegate_task` spawn tiến trình con không kiểm soát được concurrency, dễ ngâm timeout 600s làm nghẽn Event Loop của Hermes Messaging Gateway.
  2. Bị cô lập trong sandbox thiếu công cụ và môi trường chuyên dụng của Phone Farm / OmniRoute.
  3. Gây rác context và vi phạm quy chuẩn quản lý worker tập trung của farm.

---

## 2. Canonical Worker Dispatchers on Farm
Mọi tác vụ thi công code, điều tra sâu hoặc fix lỗi ngoài ngân sách O(1) của Coordinator BẮT BUỘC phải dispatch qua CLI worker chính thức:

| Priority | Tool Command | Role & Use Case |
|---|---|---|
| **1 (First Responder)** | `python D:/Taadaa/tools/sol_worker.py "<contract O(1)>" --workdir <repo>` | Độc quyền xử lý và đề xuất patch code ban đầu cho các sự cố code/test. |
| **2 (Claude / Haiku Worker)** | `python D:/Taadaa/tools/claude_worker.py "<prompt>"` / `haiku_worker.py` | Khi Sol worker timeout, crash, hoặc cần năng lực lý luận đa bước từ Claude CLI. |
| **3 (Single Gateway)** | `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo>` | Gateway dispatch tổng hợp cho các repository automation. |

---

## 3. Coordinator Protocol Before Dispatch
1. **Scope Lock O(1)**: Coordinator phải xác định rõ mục tiêu, file cần sửa, failing test/evidence trước khi gọi worker.
2. **Không spawn subagent mò mẫm**: Cung cấp exact contract và anchor duy nhất tuyệt đối.
3. **Giám sát kết quả**: Đọc stdout/exit code của worker script trực tiếp, không dựa vào self-report không kiểm chứng.
