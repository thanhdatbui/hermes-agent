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

## 3. Coordinator Protocol Before Dispatch & Gate 2 Monolith Rules
1. **Scope Lock O(1)**: Coordinator phải xác định rõ mục tiêu, file cần sửa, failing test/evidence trước khi gọi worker.
2. **Quy tắc `--anchor` trên file Monolith (> 1.500 dòng)**:
   - Cơ chế cơ giới `verify_gate2_monolith` trong `dispatch_worker.py` bắt buộc `--anchor` phải là **tên hàm hoặc class** (`def <symbol>` hoặc `class <symbol>`).
   - CẤM truyền comment, chuỗi text inline hoặc selector vào `--anchor` -> sẽ bị Gate 2 chặn ngay với lỗi `ANCHOR_NOT_FOUND (matches=0)`.
   - Hàm mục tiêu bắt buộc có độ dài `span <= 150 dòng`. Nếu target vào hàm bao quát khổng lồ (như `_feed_session_flow` dài hàng nghìn dòng) -> sẽ bị Gate 2 chặn với lỗi `SPAN_TOO_BIG`.
   - **Cách xử lý khi sửa Monolith**:
     * Hoặc target vào helper function chuyên trách có `span <= 150 dòng`.
     * Hoặc nếu là micro-fix đồng bộ biến trạng thái bên trong hàm lớn và Coordinator đã có `exact_diff_ready == TRUE` ($\le 30$ dòng, $\le 2$ files, focused test pass < 30s) -> Kích hoạt ngay **Emergency Surgery (L2)** theo đúng thẩm quyền được cấp sẵn, tránh loop dispatch fail vô ích.
3. **Giám sát kết quả**: Đọc stdout/exit code của worker script trực tiếp, không dựa vào self-report không kiểm chứng.
