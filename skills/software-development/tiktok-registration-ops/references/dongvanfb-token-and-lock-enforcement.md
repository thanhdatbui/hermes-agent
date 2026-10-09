# TikTok Registration Device Lock Enforcement (Tiktok_Reg)

## 1. Hard Lock Enforcement trong social_reg_v1.py
- Hàm `_acquire_social_device_lock_or_skip` đã được hardcode `user_authorized=True`, triệt tiêu cờ bypass `DEVICE_LOCK_ENABLED`.
- Entrypoint `register()` bắt buộc acquire lease thành công trước khi thực thi bất kỳ thao tác nào trên thiết bị:
  ```python
  dev_lease = _acquire_social_device_lock_or_skip(stt, device_id, "register")
  if dev_lease is None:
      log(f"⚠ STT {stt} đang bị khóa bởi tiến trình/cron khác -> DỪNG để đảm bảo an toàn.")
      return False
  ```
- Khối `finally:` tự động gọi `dev_lease.release()` khi hoàn tất hoặc crash.

## 2. Nguồn Mail DongVanFB (dongvanfb.net)
- **Loại 1 (ID 5 - Hotmail Trusted Graph API):** Token thiếu quyền `Mail.Read`, không đọc được qua Microsoft Graph API trên PC -> LỎ, KHÔNG DÙNG.
- **Loại 2 (ID 59):** Chỉ hỗ trợ IMAP/POP3 -> KHÔNG DÙNG.
- **Loại 3 (ID 57 - Hotmail Trusted Thêm Khôi Phục Fviainboxes):**
  - Token chuẩn full quyền `Mail.ReadWrite`, `Mail.Read`, đọc OTP trực tiếp từ PC mượt mà.
  - Phù hợp flow ngâm nick 7 ngày -> đổi pass Hotmail (sign out all devices) -> xóa mail phụ `@fviainboxes.com`.
- **Cơ chế 8 nick của TikTok:**
  - TikTok giới hạn tối đa 8 tài khoản/app.
  - Khi app đã có đủ 8 nick, nút "Thêm tài khoản" sẽ bị ẩn hoàn toàn trong dropdown switcher. Cần kiểm tra số lượng nick thực tế trên app trước khi chạy reg.
