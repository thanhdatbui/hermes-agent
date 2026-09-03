# Chẩn đoán Lỗi DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE trong Batch Reservation

## Hiện tượng
Cron nuôi acc (TikTok feed) trigger mỗi 15 phút nhưng bị crash ngay giây đầu tiên (0s), toàn bộ batch không máy nào được khởi chạy:
`runner failed before completion: DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE: operation=acquire path_index=0`

## Nguyên nhân
1. Khi khởi động batch `multi-machine-feed-session`, script loop qua danh sách máy cohort để đặt chỗ lock (`acquire_device_lock(status="queued", user_authorized=True)`).
2. `automation-core/device_lock.py` thực hiện bảo vệ atomicity bằng cách tạo file guard độc quyền `.takeover.lock` (`open("x")`) cho từng alias máy/serial trong `~/.codex/device-locks/`.
3. Nếu tồn tại file `.takeover.lock` mồ côi (do process cũ bị crash bất ngờ hoặc kill ngang) hoặc lock conflict chưa giải phóng, `_hold_path_guards` kích hoạt cơ chế fail-closed và raise `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE`.
4. Do unhandled exception ở vòng lặp đặt chỗ, chỉ cần Máy 01 dính guard lock thì toàn bộ 70+ máy khác trong cohort đều bị hoãn chạy.

## Quy trình chẩn đoán & Khắc phục
1. **Kiểm tra file guard mồ côi tại `~/.codex/device-locks/`**:
   ```bash
   ls -la ~/.codex/device-locks/.*.takeover.lock
   ```
2. **Kiểm tra tiến trình sở hữu lock cũ**:
   Kiểm tra PID trong file lock qua `tasklist /FI "PID eq <pid>"`.
3. **Dọn dead locks**:
   Chạy script dọn lock hoặc đợi cronjob `reap-dead-owner-locks` (`b63730cc5c85`) xử lý:
   ```bash
   python "D:\Taadaa\tiktok-luot nuoi acc\scripts\reap-dead-owner-locks.py"
   ```
4. **Xác nhận phục hồi**:
   Khi file guard / dead lock được dọn dẹp, đợt cron tiếp theo (mỗi 15m) sẽ reserve lock thành công và khởi chạy bình thường.
