# GuardGate Invariant Anonymous Block & Cơ Chế Auto-Wire Preflight Guidance (2026-11-04)

## 1. Bối Cảnh Vi Phạm GuardGate Invariant
- **Rule ID:** `case_invariant_require_step_by_step_structure`
- **Cơ chế kiểm tra:** Hàm `check_step_by_step_structure` trong `D:/Taadaa/tools/guardgate/predicates.py`.
- **Ngưỡng vi phạm:** Khi diff thêm mới trong file `.py` có từ **15 dòng code thực thi trở lên** (không tính dòng trống, docstring, import) mà **không có comment định danh bước** khớp regex:
  `r"#.*(buoc|bước|step|phase|stage|checkpoint)|#\s*={3,}"` (ignore case).
- **Hậu quả Closeout Gate:** `closeout_gate.py` trả về `DENY` (`verdict: REJECTED, score: 0`), chặn đứng toàn bộ tiến trình commit và push.

## 2. Khắc Phục Khoảng Trống Auto-Wire (Pre-flight Injection)
- **Vấn đề cũ:** GuardGate chỉ thực thi ở chế độ **Hậu Kiểm (Reactive Enforcement)** tại cổng Closeout Gate hoặc khi commit. Worker lúc nhận task không biết luật này nên viết code không gắn `# Step X` $\rightarrow$ bị chặn và tốn thêm vòng lặp sửa lại.
- **Giải pháp cơ giới hóa hoàn tất:**
  - Tích hợp hàm `resolve_guardgate_guidance(target_file)` trực tiếp vào `D:/Taadaa/tools/dispatch_worker.py`.
  - Hàm tự động đọc SSOT `D:/Taadaa/tools/guardgate/rules.json` (dạng `list[dict]`), trích xuất toàn bộ trường `guidance` của các Invariant rules đang active.
  - Tự động tiêm khối `[GUARDGATE INVARIANT GUIDANCE]` vào `effective_prompt` trước khi chuyển giao task cho Worker (Sol/Gemini/Haiku).
  - Khối hướng dẫn bao gồm:
    * `Chia nhỏ logic và thêm comment định danh bước rõ ràng trước các khối logic chính (# Step X).`
    * `Android http_proxy bắt buộc dùng IP LAN nội bộ 192.168.110.2:<port>, cấm gán hostname/domain ngoài.`
    * `Ghi file trực tiếp; không dump chuỗi base64 ra terminal.`
    * `Xóa lệnh uiautomator dump; ưu tiên trích xuất text qua WinRT OCR...`

## 3. Thẩm Định Độc Lập Từ Hội Đồng Cố Vấn (Advisors Sol & Gemini)
- **Advisor Sol (GPT-5.6):** Phê duyệt kiến trúc tập trung via `rules.json`, xác nhận luồng Preflight Guidance giúp triệt tiêu vòng lặp sửa lại (First-pass Yield tăng cao).
- **Advisor Gemini (Argon 4):** Lưu ý rủi ro I/O blocking nếu đọc file lặp đi lặp lại khi scale-up; khuyến nghị giữ số lượng gạch đầu dòng $\le 10$ để tránh bẫy Attention Dilution.
- **Bộ test kiểm chứng:** Đã bổ sung `test_resolve_guardgate_guidance` vào `tests/test_dispatch_worker.py` (32/32 tests pass).

## 4. Kỷ Luật & Quy Chuẩn Cho Coordinator / Worker
1. **Chủ động chia bước trong Prompt & Code:** Khi sửa code có khối logic mới $\ge 15$ dòng, bắt buộc phải chèn comment:
   - `# Step 1: <Mô tả bước 1>`
   - `# Step 2: <Mô tả bước 2>`
   - `# Step 3: <Mô tả bước 3>`
2. **Kẹp chặt Test Delta:** Sửa file logic Python luôn phải cập nhật hoặc bổ sung test case tương ứng trong `tests/test_<file>.py` để tránh vi phạm `MANDATORY_TEST_DELTA_VIOLATION`.
3. **Theo dõi Watchdog:** Rule này đã được nạp và theo dõi qua `gate_compliance_watchdog.py` (Gate G4), bất kỳ vi phạm nào đều bị ghi vết vào `tools/guardgate/ledger.jsonl` và báo cáo định kỳ 6h về Telegram.
