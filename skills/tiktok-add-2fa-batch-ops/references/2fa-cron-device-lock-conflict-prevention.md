# Quản lý Device Lock & Tránh xung đột giữa 2FA và Cron Nuôi Acc (2026-08-25)

## 1. Cơ chế hoạt động của `acquire_device_lock` trong `automation-core`
- Khi gọi `acquire_device_lock`:
  - `user_authorized=True`: Tạo file `.lock.json` vật lý trên ổ cứng (`C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`).
  - `user_authorized=False`: KHÔNG tạo file lock trên đĩa, chỉ trả về `_UnlockedDeviceLockLease` (chạy dạng không khóa).
- **Hậu quả nếu dùng `user_authorized=False`:**
  - Cron nuôi acc (`tiktok_runner.py` / `multi_machine_feed_session.py`) khi đến lịch quét sẽ kiểm tra thư mục lock.
  - Vì không thấy file `.lock.json` của 2FA, Cron xem máy đang rảnh và nhảy vào điều khiển thiết bị, dẫn tới đá app, mất focus và gây lỗi `TikTok focus lost`.

## 2. Quy tắc bắt buộc khi chạy Batch 2FA
- Trong `run_batch_live_2fa.py`, khi giữ chỗ (reservation) cho thiết bị, bắt buộc phải dùng `user_authorized=True` (commit `6927897`).
- Khi có file lock thật, Cron nuôi acc gặp máy đó sẽ tự động ghi nhận `SKIPPED_LOCKED` và bỏ qua an toàn, không tranh chấp thiết bị.

## 3. Pitfall: Script con dùng `finally: lock.release()` làm hở máy giữa chừng
- **Hiện tượng (hit 25/08 chiều trên M26 & M27):** User ra lệnh chạy script thử OTP/bật 2FA trên máy lẻ. Code script có `lock = acquire_device_lock(..., user_authorized=True)` nhưng bọc trong `finally: lock.release()`.
- **Nguyên nhân gây lỗi:** Khi script 2FA kết thúc (hoặc gặp lỗi ở bước đọc OTP/giao diện và dừng lại), khối `finally` tự động xóa file `.lock.json` khỏi đĩa, dù màn hình máy vẫn đang dừng dở ở app Outlook hoặc popup xác minh. Cron nuôi acc quét thấy thư mục lock trống liền nhảy vào điều khiển làm văng app / `TikTok focus lost`.
- **Quy tắc sửa:** Khi user yêu cầu lock máy hoặc thực hiện tác vụ cần can thiệp thủ công/chờ xử lý tiếp, KHÔNG gọi `lock.release()` tự động trong `finally` nếu tác vụ chưa hoàn tất thành công (`status != success`). Phải giữ lock ở trạng thái `handoff` hoặc `blocked` (`lease.finish(succeeded=False)`) để cron bỏ qua máy cho tới khi user/operator mở khóa.
