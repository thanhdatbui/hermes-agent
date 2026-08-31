# Anti-Hang & 3-Strike Loop Breaker Protocol (2026-08-31)

## 1. Anti-Hang & Hard Timeout Gate
- **Nguyên nhân treo 45p - 2h**:
  1. Thiếu socket timeout khi gọi API/9Router/Omni/CLI với diff lớn -> urllib/requests treo vô hạn.
  2. Subprocess/terminal/pytest kẹt `stdin` hoặc deadlock tài nguyên.
  3. Tin nhắn mới từ Telegram đóng vai trò out-of-band interrupt hủy turn bị treo.
- **Quy tắc Timeout**:
  - `HTTP_TIMEOUT_QUICK = 120s` (lệnh đơn, probe, context nhỏ).
  - `HTTP_TIMEOUT_HEAVY = 500s` (diff lớn, model lớn với thinking high).
  - Subprocess/Pytest: Luôn set `timeout = 120s - 300s`, kèm cờ non-interactive (`-y`, `-b`).
  - Quá timeout -> Bắt ngoại lệ, in mã lỗi `AUDIT_TIMEOUT`, fail-closed chuyển ngay sang fallback route (không đứng chờ).

## 2. 3-Strike Loop Breaker (Chống Vòng Lặp Vô Hạn)
- **Tách biệt**: Timeout mạng/tiến trình ĐỘC LẬP với số strike logic code.
- **Audit Review Strike**:
  - Nếu Auditor `REJECT` hoặc `MINOR_FIXES` **3 vòng liên tiếp** cùng 1 vấn đề/root-cause:
    - BẮT BUỘC DỪNG TOÀN BỘ.
    - Báo cáo rõ điểm bất đồng (Auditor finding vs Worker solution).
    - Hỏi ý kiến user, cấm tự động sửa vòng 4.
- **TDD Worker Strike**:
  - Nếu Worker chạy pytest fail cùng 1 test **3 lần liên tiếp** dù đã thử 3 patch khác nhau:
    - Rollback code dở dang, đánh dấu `WORKER_BLOCKED_STRIKE_3`.
    - Trả quyền điều phối cho Coordinator để xin ý kiến.

## 3. Workflow Intent Recognition
- Khi user nói "Dùng 6 bước thiết kế / làm đi", đây là lệnh KÍCH HOẠT QUY TRÌNH:
  1. Viết plan `.hermes/plans/YYYY-MM-DD_<name>.md`.
  2. Gửi 9Router audit plan lấy `VERDICT: APPROVED`.
  3. Dispatch Worker TDD Red -> Green.
- TUYỆT ĐỐI không nhầm lẫn là đi sửa text file rule / AGENTS.md.
