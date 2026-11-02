---

name: hotmail-outlook-automation

description: Hotmail automation.

---
# Hotmail/Outlook Automation

- **BoxTaiKhoan API**: Buy OAuth2 product 60 via `POST /ajaxs/client/product.php`, one account per request (`amount=1`) to receive complete `data`; format `mail|pass|refresh_token|client_id`.
- **Change-pass eligibility (2026-10-10)**: Cần TikTok ID+pass & ChatGPT PASS (Col 12), xóa Col 9 sau khi thành công.
- **6H report reconciliation**: Đọc state canonical trước khi xác định nguyên nhân. Xem `references/6h_report_snapshot_reconciliation.md`.
- **GPM login verification & skip-link pitfalls (2026-10-21)**: Dùng endpoint đích có wreply `account.live.com/proofs/manage/additional`, cấm selector `a:has-text('Bỏ qua')` (tránh bấm nhầm uhf-skip-link), chống false positive trang promo landing. Xem `references/microsoft_gpm_login_verification_pitfalls.md`.
- **Bắt buộc có Mail khôi phục trước khi bật 2FA TOTP (2026-10-13)**: Cần 2 phương thức xác minh (Pass + Mail khôi phục) trước khi bật 2FA. Dùng domain tạm `@fviainboxes.com`. Xem `references/hotmail_change_info_recovery_and_2fa_flow.md`.
- **Phạm vi Dual-Farm (Kibe + Admin)**: Toàn bộ 2 farm ~1.280 tài khoản (Kibe 1-80: 640, Admin 201-280: ~640). Không đếm thiếu cụm Admin.
- **Kiến trúc kho Gmail Clean V2 & 2 Cột Trạng Thái (2026-08-25)**:
  - `gmail_clean_v2.xlsx` là **Single Source of Truth** chứa cả Gmail và Hotmail của farm.
  - Cột 11: `info_changed` (đánh dấu `1` khi đã đổi info/pass bảo mật Hotmail).
  - Cột 12: `app_logged_in` (đánh dấu `1` khi đã login vào Outlook app trên thiết bị).
  - Hotmail mới mua về nạp thẳng vào `gmail_clean_v2.xlsx` (để trống 2 cột này). Script reg TikTok (`_detect_clean.py`) tự quét các mail chưa có ID TikTok trong `taikhoan_dat_v2_updated .xlsx` để chạy.
  - **Quarantine Mail Lỗi**: Tài khoản bị lỗi token, die, hoặc không lấy được OTP bắt buộc XÓA khỏi `gmail_clean_v2.xlsx` và lưu vào `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt` để chống script chọn lại gây kẹt vòng lặp.
  - **Mail Khôi Phục Domain Riêng & Change-Info Pipeline**: CẤM coi mail domain (`fviainboxes.com`, `smvmail.com`) là mail ảo. Đọc OTP qua API và quy trình Sign out everywhere + re-login kiểm chứng: xem chi tiết tại `references/mail-domain-recovery-otp.md`.
- **Chống xoay ngang màn hình (Rotation Lock)**: Phải chạy đầy đủ `settings put` + `content insert` vào `system:accelerometer_rotation=0` và `user_rotation=0` trước khi mở Outlook.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
