# Churn Metrics & Auto-Rewire Audit Classification

## 1. Bối Cảnh Thực Nghiệm Vận Hành (Empirical Finding)
Khi đối soát log vận hành đa phiên (như `dispatch.jsonl`, `dispatch_audit.jsonl`, `guard_scan_audit.jsonl`), số lượt agent "loay hoay" (churn turns) phụ thuộc trực tiếp vào cơ chế can thiệp của Gate:
- **Guidance Text thụ động (Chặn + Hướng dẫn text):** Agent mất trung bình **3 – 5 lượt** mới định dạng lại đúng contract (thử sai nhiều biến thể trước khi đọc kỹ cú pháp).
- **Auto-Rewire chủ động (Tự viết lại payload ngầm):** Agent tốn **0 lượt** (hoàn toàn transparent, zero-turn overhead).
- **Rào cản thông số cục bộ (Timeout, Root Scope):** Agent mất **1 – 2 lượt** để điều chỉnh lại flag.

## 2. Tiêu Chuẩn Phân Loại Vi Phạm Gate Trong Báo Cáo Watchdog
CẤM đánh đồng mọi lần chạm Guard là "FAIL". Một hệ thống GuardGate lành mạnh phải phân loại thành 3 trạng thái:

1. **PASS (Tuân thủ ban đầu):** Thao tác chuẩn contract ngay từ lệnh đầu tiên.
2. **REWIRED / RECOVERED (Tự chữa lành thành công):**
   - **Auto-Rewired (0-turn):** Pre-tool hook tự động rewrite/clamp tham số an toàn (ví dụ: auto-clamp budget 15 -> 8, auto-rewire cờ `--skip-test`).
   - **Guidance Recovered (<= 1 turn):** Agent bị block nhưng turn kế tiếp điều chỉnh đúng đường ngay lập tức dựa trên guidance của hook.
   - *Đánh giá:* **HỢP LỆ (COMPLIANT)**. Đây là bằng chứng của self-healing, không được tính vào lỗi hệ thống.
3. **LOOP / DEADLOCK FAIL (Vi phạm thực sự):**
   - Agent loay hoay lặp lại cùng một kiểu lỗi $\ge 3$ lượt liên tiếp trên cùng correlation/session mà không tự thoát.
   - Worker dispatch rơi vào trạng thái cạn budget hoặc bế tắc mà không có active pivot.
   - *Đánh giá:* **FAIL (NON-COMPLIANT)**, cần báo động Operator/Coordinator can thiệp.

## 3. Quy Tắc Cô Lập Dữ Liệu Test (Test Artifact Pollution Invariant)
- **Hiện tượng:** Bộ test suite (pytest) chạy các test case kiểm thử rào chắn (negative testing) thường ghi trực tiếp vào log audit production nếu không được cô lập. Điều này tạo ra hàng chục bản ghi `QUOTA`, `TIMEOUT`, `NEEDS_INPUT` ảo (chiếm tới 75% số liệu vi phạm trong các đợt đối soát 6h).
- **Quy chuẩn Watchdog:**
  - Báo cáo audit BẮT BUỘC có bộ lọc loại bỏ các bản ghi mang dấu vết test: `pytest-of-`, thư mục tạm `AppData/Local/Temp`, hoặc target file mock giả lập (`target.py`).
  - Unit test cho các hook guard BẮT BUỘC dùng mock hoặc trỏ audit log ra fixture `tmp_path`, cấm ghi đè trực tiếp vào file log production (`D:/Taadaa/logs/*` hoặc `D:/Taadaa/runtime/audit_logs/*`).
