# Pre-Session Device Readiness Gate & Idempotency Receipt Auto-Archive (2026-10-21)

## 1. Bối Cảnh Thực Tế & Điểm Mù Hệ Thống
1. **Sự cố Máy 74 treo 3 tuần:**
   - Máy 74 (SM-G930F, serial `ce061606c21e153d03`) bị treo socket transport daemon ADB kéo dài suốt 3 tuần, khiến 5 nick kẹt không đăng bài và không được nuôi.
   - Nguyên nhân: `vpn_preflight.py` chỉ gọi `adb.reconnect()` khi check VPN timeout. Nếu socket đã treo từ trước, các lệnh ADB trước đó bị block cứng.
   - Runner `tiktok_runner.py` thiếu bước Pre-Session Readiness Gate, giao việc mù cho toàn bộ Row mà không ping kiểm tra thiết bị còn sống hay không.
2. **Sự cố Máy 4 kẹt 16-20 ngày (Idempotency Receipt Trap):**
   - File receipt `machine_4_account_thuuy.thy_video_30.json` bị dở dang ở trạng thái `intent_pending` + `post_submission_state: UNKNOWN` từ ngày 05/10.
   - `state_machine.py:8297-8315` quét toàn bộ pending receipts mà **không có TTL/hạn sử dụng**.
   - Khi `pending_video >= cursor`, state machine ép sang `VERIFY_POST`, bị rule `COMPAT-POST-VERIFY-004` chặn ở `MANUAL_REVIEW` nhưng không xóa cũng không archive receipt trên đĩa.
   - Hậu quả: deadlock vĩnh viễn qua hơn 40 ca chạy liên tiếp.

---

## 2. Kiến Trúc 2 Trụ Cột Khắc Phục Triệt Để

### Trụ Cột 1: Pre-Session Device Readiness Gate (`pre_session_device_gate.py`)
- **Fast Probe Song Song O(1) (timeout 3.0s):**
  Lấy serial qua `get_serial_for_machine()`, chạy `adb -s <serial> get-state` với `run_subprocess` ép cờ `CREATE_NO_WINDOW` (chống nháy console desktop).
- **Phân Tầng Cứu Hộ Tự Động:**
  * Nếu probe `get-state` trả về khác `device` hoặc timeout/exception:
    1. Kiểm tra Blackout cửa sổ Reboot (`is_reboot_blackout()`): Khung giờ `05:10-05:35`, `11:10-11:45`, `17:10-17:35` $\rightarrow$ Đánh dấu `recovery_deferred`, không kích hoạt USB reset tránh xung đột POST BIOS.
    2. Nếu ngoài Blackout: Gọi `recover_device()` từ `recover_stuck_s7.py` (Level 1 Soft Recovery $\rightarrow$ Level 3 USB Hub Port Reset).
    3. Re-probe lại: Nếu online $\rightarrow$ `status: recovered`; nếu vẫn hỏng $\rightarrow$ `status: recovery_failed`.
- **Lọc Máy Khỏe Mạnh (`filter_healthy_machines`):**
  Chỉ trả về danh sách các máy `ready` hoặc `recovered`. Máy chết vật lý / tuột cáp bị loại ra để không làm nghẽn tiến trình batch của các máy còn lại trong Row.
- **Kill-Switch Bảo Vệ:** `AUTO_RECOVERY_ENABLED=0` cho phép vô hiệu hóa tức thời logic cứu hộ mà không cần sửa code.
- **Unit Tests:** 56/56 tests passing trong `tests/test_pre_session_device_gate.py`.

### Trụ Cột 2: Tự Động Hóa Vòng Đời Receipt (`reconcile_stale_post_receipts.py`)
- **Điều Kiện Kép An Toàn:** Chỉ dọn các file có `mtime >= 24.0h` **VÀ** status $\in$ {`intent_pending`, `verification_pending`, `retry_intent_pending`} hoặc `submission_state == "UNKNOWN"`. Tuyệt đối không chạm receipt đã `completed` hoặc $< 24$h để bảo vệ idempotency.
- **Lock-Safety & Non-blocking Retry:** Thử di chuyển 3 lần x 500ms khi gặp `PermissionError` (chống race condition khi runner đang ghi file). Hết 3 lần thì skip an toàn.
- **Chế Độ Silent Watchdog:**
  Script wrapper `cron_reconcile_stale_receipts.py` hoàn toàn im lặng (stdout rỗng) khi 0 có receipt kẹt; chỉ xuất báo cáo khi có file được di chuyển sang `archived_stale/`.
- **Hermes Cron:** Đăng ký job `hourly-stale-post-receipts-reconcile` (chu kỳ `20 * * * *`, chạy vào phút 20 mỗi giờ).
