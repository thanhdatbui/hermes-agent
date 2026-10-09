# Post Noon Chain Watchdog & Blocked Device Lock Idle Gate

## 1. Hành vi của `post_noon_chain_watchdog.py` với `--force`
- Cờ `--force` trong `post_noon_chain_watchdog.py` chỉ bypass:
  1. Khung giờ chạy (14:30 - 17:30 HCM).
  2. Kiểm tra Ca 2 kết thúc (`is_ca2_finished`).
  3. Kiểm tra idempotency (`already_ran_today`).
- **CẤM NHẦM LẪN:** `--force` **KHÔNG** bypass kiểm tra `has_active_device_locks()` và `is_feed_runner_active()`.
  ```python
  if is_feed_runner_active() and not args.dry_run:
      return 0
  if has_active_device_locks() and not args.dry_run:
      return 0
  ```
  Nếu còn bất kỳ lock nào (`active`, `running`, `queued`, `blocked`), script sẽ âm thầm thoát với mã `0`.

## 2. Blocked Lock Retention & Phối hợp Reaper
- Khi một máy trong ca feed gặp lỗi nghiêm trọng (focus issue, popup lạ, ADB offline), feed runner chuyển lock máy đó sang trạng thái `blocked` kèm mốc `handoff_at`.
- Trạng thái `blocked` có TTL an toàn là **60 phút** (giữ hiện trường phục vụ operator triage). Dù tiến trình chủ (PID) đã chết (`owner_active == False`), Reaper vẫn **giữ nguyên lock** cho tới khi đủ 60 phút từ `handoff_at` hoặc `started_at`.
- Khi kiểm tra điều kiện kích hoạt chuỗi sau ca nuôi (Reg Gmail -> Add 2FA):
  1. Không được chỉ kiểm tra `is_feed_runner_active()` hoặc PID chủ đã chết.
  2. Bắt buộc kiểm tra `has_active_device_locks()` trong cả `C:\Users\Kibe\AppData\Local\automation-core\device-locks` và `C:\Users\Kibe\.codex\device-locks`.
  3. Nếu còn lock `blocked` chưa hết TTL 60 phút, chuỗi kế tiếp không thể chạy ngay mà phải chờ Reaper định kỳ thu hồi sau khi hết hạn.
