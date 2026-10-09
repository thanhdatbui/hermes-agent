# TikTok Registration Safety & Device Lock Enforcement

> Sự cố 23/09/2026: Tránh phá hoại chéo giữa script test và các tiến trình farm khác (2FA, nuôi acc).

## 1. Cơ Chế Hard Lock Bắt Buộc
- Trong `social_reg_v1.py`, hàm `_acquire_social_device_lock_or_skip` BẮT BUỘC đặt cứng `user_authorized=True` (đã xóa vĩnh viễn cờ `DEVICE_LOCK_ENABLED`).
- Tại hàm `register()`, bắt buộc acquire `dev_lease = _acquire_social_device_lock_or_skip(...)` TRƯỚC KHI thực hiện bất kỳ thao tác nào:
  - Nếu `dev_lease is None` -> Log cảnh báo và `return False` ngay lập tức. Cấm chạm vào ADB hay TikTok.
  - Toàn bộ khối thực thi bọc trong `try...finally: dev_lease.release()` để đảm bảo không bị lock leak khi exception.

## 2. Kiểm Tra Mail Trước Khi Reg
- Khi mua Hotmail từ `dongvanfb.net`:
  - **ID 57 (HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM - 350đ)**: Scope token Graph API đầy đủ (`Mail.Read`, `Mail.ReadWrite`), dùng được cho tool farm đọc OTP tự động. Phù hợp flow ngâm 7 ngày đổi pass + xóa mail khôi phục.
  - **CẤM ID 5 / ID 59**: Thiếu quyền `Mail.Read`, gọi Graph API bị từ chối (`Graph token invalid`).
- Không chạy đè tài khoản trên máy đã đạt ngưỡng 8 tài khoản (TikTok tự ẩn nút 'Thêm tài khoản').
