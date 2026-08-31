# Anti-Hang & 3-Strike Loop Breaker Protocol (2026-08-31)

## 1. Anti-Hang & Hard Timeout Gate
- **Nguyên nhân treo 45p - 2h**:
  1. Thiếu socket timeout khi gọi API/9Router/Omni/CLI với diff lớn -> urllib/requests treo vô hạn.
  2. Subprocess/terminal/pytest kẹt `stdin` hoặc deadlock tài nguyên.
  3. Tin nhắn mới từ Telegram đóng vai trò out-of-band interrupt hủy turn bị treo.
- **Quy tắc Timeout (Module: `D:\Taadaa\tools\anti_hang_guard.py`)**:
  - `HTTP_TIMEOUT_QUICK = 120.0s` (lệnh đơn, probe, context nhỏ).
  - `HTTP_TIMEOUT_HEAVY = 500.0s` (diff lớn, model lớn với thinking high).
  - `PROCESS_TIMEOUT_DEFAULT = 180.0s` (subprocess/pytest).
  - Mọi subprocess bắt buộc: `stdin=subprocess.DEVNULL`, `NONINTERACTIVE=1`, `CI=1`, `PYTHONUNBUFFERED=1`.
  - Quá timeout -> Bắt ngoại lệ, in mã lỗi `AUDIT_TIMEOUT`, fail-closed chuyển ngay sang fallback route (không đứng chờ).

## 2. 3-Strike Loop Breaker (Chống Vòng Lặp Vô Hạn)
- **Tách biệt**: Timeout mạng/tiến trình ĐỘC LẬP với số strike logic code.
- **Fingerprinting Chặt Chẽ**: Dùng SHA256 JSON serialization của `[location, error_type, description]` chuẩn hóa chống collision ký tự đặc biệt.
- **Audit Review Strike (`AuditStrikeTracker`)**:
  - Thread-safe (`threading.Lock()`).
  - Nếu Auditor `REJECT` hoặc `MINOR_FIXES` **3 vòng liên tiếp** cùng 1 vấn đề/root-cause:
    - Tự động ném `StrikeLimitReachedException`.
    - BẮT BUỘC DỪNG TOÀN BỘ.
    - Báo cáo rõ điểm bất đồng (Auditor finding vs Worker solution).
    - Hỏi ý kiến user, cấm tự động sửa vòng 4.
- **TDD Worker Strike (`WorkerStrikeTracker`)**:
  - Nếu Worker chạy pytest fail cùng 1 test **3 lần liên tiếp** dù đã thử 3 patch khác nhau:
    - Rollback code dở dang, đánh dấu `WORKER_BLOCKED_STRIKE_3`.
    - Trả quyền điều phối cho Coordinator để xin ý kiến.

## 3. Workflow Intent Recognition
- Khi user nói "Dùng 6 bước thiết kế / làm đi", đây là lệnh KÍCH HOẠT QUY TRÌNH:
  1. Viết plan `.hermes/plans/YYYY-MM-DD_<name>.md`.
  2. Gửi 9Router audit plan lấy `VERDICT: APPROVED`.
  3. Dispatch Worker TDD Red -> Green.
  4. Review diff độc lập lấy `VERDICT: APPROVED`.
  5. Chạy Isolated Pytest.
  6. Rebase, Commit & Push.
- TUYỆT ĐỐI không nhầm lẫn là đi sửa text file rule / AGENTS.md.
