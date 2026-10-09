# Hotmail DongVanFB & Device-Lock Enforcement Reference (2026-09-23)

## 1. Phân loại Hotmail trên dongvanfb.net cho Farm Taadaa

| ID | Tên sản phẩm trên sàn | Đơn giá | Scope Token Microsoft Graph | Khả năng đọc OTP qua PC | Độ phù hợp với Flow Taadaa |
|---|---|---|---|---|---|
| **ID 5** | Hotmail TRUSTED [GRAPH API] | 350đ | IMAP, POP, SMTP (THIẾU `Mail.Read`) | ❌ Bị Microsoft từ chối (`Graph token invalid`) | **LỎ — CẤM MUA** |
| **ID 59** | Hotmail TRUSTED [IMAP/POP3/GRAPH API] | 350đ | Tương tự ID 5, chủ yếu cho tool giả lập | ❌ Thiếu scope Graph API | **CẤM MUA** |
| **ID 57** | HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM | 350đ | `User.Read`, `Mail.ReadWrite`, `Mail.Read`, IMAP, POP, SMTP | ✅ 100% qua Microsoft Graph API | **CHUẨN 100% — NÊN MUA** |

### Flow vận hành chuẩn với ID 57 (350đ):
1. Mua mail qua API dongvanfb (`account_type=57`).
2. Nạp token vào `gmail_clean_v2.xlsx`, tool Farm đọc OTP tự động qua Microsoft Graph API mà không cần mở app Outlook trên phone.
3. Reg TikTok xong, ngâm tài khoản 7 ngày.
4. Sau 7 ngày: Đăng nhập Hotmail trên web/PC -> Đổi mật khẩu -> Chọn *"Sign me out of all devices"* (đá sạch thiết bị cũ của sàn) -> Vào *Advanced Security Options* xóa mail khôi phục `@fviainboxes.com` -> Thêm mail khôi phục/SĐT cá nhân. Tài khoản thuộc quyền sở hữu riêng 100%.

---

## 2. Hard Device-Lock Enforcement (Chống xung đột đa tiến trình)

### Bài học cốt tử:
- **CẤM TUYỆT ĐỐI Coordinator tự ý force-stop hoặc bấm HOME:**
  - Không được can thiệp vào máy khi chưa kiểm tra `~/.codex/device-locks/machine_<N>.lock.json`.
  - Màn hình lạ (như *"Thiết lập xác minh 2 bước"*, Authenticator, Upload...) có thể là flow của tiến trình khác đang chạy (Add 2FA, Upload, Feed). Tự ý force-stop sẽ phá hủy phiên làm việc của script khác.
- **Quy tắc Force-stop khi test:**
  - Vẫn cần thiết để reset app về clean state, **NHƯNG CHỈ ĐƯỢC PHÉP TRÊN MÁY DO CHÍNH TIẾN TRÌNH ĐÓ ĐANG GIỮ LOCK HỢP LỆ (PID KHỚP)**.
- **Cơ chế Reaper Cron:**
  - `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py` chạy định kỳ với TTL 3600s (1h).
  - Tự động phát hiện lock chết (owner process dead) hoặc quá hạn 1h -> chuyển vào quarantine -> force-stop và đưa máy về Home an toàn.
- **Cơ chế khóa trong `social_reg_v1.py`:**
  - Cấm cờ opt-in `DEVICE_LOCK_ENABLED`. Luôn ép cứng `user_authorized=True` trong `_acquire_social_device_lock_or_skip`.
  - Entrypoint `register()` phải acquire device lock trước khi thao tác. Nếu `dev_lease is None` -> DỪNG NGAY (SKIP), cấm bypass.
