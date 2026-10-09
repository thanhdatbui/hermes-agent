# Incident 23/09/2026: Hard Lock Enforcement vs Tunnel-Vision Interventions

## 1. Bản chất sự cố
Coordinator khi chạy test reg TikTok đã tự ý chạy lệnh `am force-stop` và `input keyevent 3` (HOME) trên Máy 42 khi thấy màn hình dừng ở "Thiết lập xác minh 2 bước". Thực tế trên farm lúc đó tiến trình `run_batch_live_2fa.py` đang chạy xử lý 2FA cho các tài khoản. Hành động này phá vỡ tiến trình hợp lệ đang chạy của người dùng.

## 2. Nguyên nhân kỹ thuật cốt lõi
1. **Lỗ hổng Bypass Lock trong `social_reg_v1.py`**:
   Trước đây code có dòng kiểm tra opt-in:
   ```python
   lock_enabled = os.environ.get("DEVICE_LOCK_ENABLED", "").strip().lower() in {"1", "true", "yes"}
   ```
   Khi chạy CLI đơn lẻ `python social_reg_v1.py <stt> ...`, biến này không được set (`False`) dẫn đến bỏ qua hoàn toàn `acquire_device_lock` của `automation-core`, không tạo file `machine_<N>.lock.json`.
2. **Coordinator Tunnel-Vision**:
   Coordinator coi màn hình lạ là "treo/kẹt" và tự cho mình quyền "dọn dẹp" mà không kiểm tra xem máy có đang thuộc sở hữu của flow khác không.
3. **Lệnh ADB thô không có guard**:
   Các lệnh `adb shell am force-stop` được gọi trực tiếp mà không kiểm tra trạng thái lock của máy.

## 3. Quy tắc Invariant bắt buộc đã được áp dụng
- **Xóa vĩnh viễn cơ chế Opt-in `DEVICE_LOCK_ENABLED`**: Mọi entrypoint trong `social_reg_v1.py` (đặc biệt là hàm `register()`) bắt buộc phải gọi `acquire_device_lock` với `user_authorized=True`.
- **Chặn đứng ngay tại cửa ngõ `register()`**:
  ```python
  dev_lease = _acquire_social_device_lock_or_skip(stt, device_id, "register")
  if dev_lease is None:
      log(f"⚠ STT {stt} đang bị khóa bởi tiến trình/cron khác -> DỪNG để đảm bảo an toàn.")
      return False
  ```
- **Bảo toàn Lock của PID sống**: Nếu một file lock thuộc về một PID đang tồn tại và hoạt động (`psutil.pid_exists(pid)`), không có bất kỳ tiến trình ngoài lề hay Coordinator nào được phép release hay force-stop thiết bị đó.
- **Reaper Cron 1 giờ (TTL = 3600s)**: Script `reap-dead-owner-locks.py` chỉ thu hồi lock và đưa máy về Home khi:
  1. Lock đã tồn tại quá 1 giờ (TTL expired).
  2. Hoặc tiến trình sở hữu (PID) đã chết hoàn toàn (`owner_alive is False`).
