# Hard Device-Lock Enforcement & Cross-Process Safety (2026-09-23)

## 1. Bối cảnh sự cố & Phân tích nguyên nhân
- **Hiện tượng:** Coordinator thấy app trên máy ở màn hình lạ (màn hình cài đặt 2FA Authenticator), suy diễn là "treo/kẹt", tự ý gửi lệnh `am force-stop` và bấm `keyevent 3` (HOME) để đưa máy về trạng thái trống phục vụ tác vụ của mình.
- **Hậu quả:** Phá vỡ tiến trình `tiktok-add-bao-mat-f2a` đang thực thi hợp lệ trên thiết bị.
- **Lỗ hổng kiến trúc cốt tử phát hiện được:**
  1. `social_reg_v1.py` dùng cờ opt-in `DEVICE_LOCK_ENABLED = os.environ.get(...)` mặc định `False` khi chạy CLI đơn lẻ -> bypass hoàn toàn `acquire_device_lock` của `automation-core`.
  2. Coordinator gọi lệnh ADB thô (`subprocess adb shell am force-stop`) trực tiếp không kiểm tra file lock `~/.codex/device-locks/machine_<N>.lock.json`.

## 2. Invariants & Quy tắc điều phối bất biến
1. **Doubt -> Freeze -> Hands-off:**
   - Khi quan sát thấy màn hình không thuộc flow của mình: TUYỆT ĐỐI KHÔNG TỰ Ý FORCE-STOP, KHÔNG BẤM HOME, KHÔNG GIẢI PHÓNG RESERVATION CỦA TIẾN TRÌNH KHÁC.
2. **Quyền hạn Force-stop:**
   - Thao tác force-stop khi test đồ/reset app là hợp lệ, **NHƯNG CHỈ ĐƯỢC PHÉP THỰC HIỆN TRÊN MÁY DO CHÍNH TIẾN TRÌNH ĐÓ ĐANG GIỮ LOCK HỢP LỆ (PID KHỚP)**.
3. **Hard-coded Lock (Cấm Opt-in):**
   - Mọi script can thiệp vào máy farm bắt buộc phải acquire `device_lock` với `user_authorized=True`.
   - Nếu `dev_lease is None` (máy đang có lock của tiến trình/cron khác) -> LẬP TỨC ABORT / SKIP, cấm chạy tiếp.
4. **Reaper Cron:**
   - Hệ thống có script `reap-dead-owner-locks.py` (TTL 3600s / 1h) tự động quét dọn lock mồ côi (owner PID dead) hoặc hết hạn 1h và reset thiết bị an toàn. Coordinator không được tranh quyền với Reaper.
