# ACCOUNT MISSING TRIAGE & 2FA ACCOUNT PRESERVATION DISCIPLINE

## 1. Bối cảnh & Sự cố (Incident 10/10/2026 - Máy 20 / @anhdo829)
- **Triệu chứng alert**: `UploadHook: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.`
- **Sai lầm nhận định của Agent**: Thấy nick mục tiêu `@anhdo829` (liên kết Gmail `dotranganh221220002212@gmail.com`) có Gmail nằm trong `gmail_die_tong.txt`, agent vội vàng kết luận "tài khoản TikTok đã die", rồi tự ý khai tử trên Master Excel và thay bằng nick mới.
- **Hậu quả**: Suýt vứt bỏ một tài khoản cổ 7 tháng tuổi, 21 video, 116 followers, 428 tim đang hoạt động bình thường trên TikTok.

## 2. Invariants Bắt Buộc Khi Xử Lý Cảnh Báo ACCOUNT_MISSING

### Quy tắc 1: CẤM ĐÁNH ĐỒNG GMAIL DIE VỚI TIKTOK DIE
- Gmail liên kết bị khóa/die **KHÔNG ĐƯỢC PHÉP** coi là TikTok die.
- TikTok có thể đăng nhập bằng Username + Password + 2FA TOTP Authenticator, hoàn toàn không cần OTP Gmail.
- Trước khi phân loại nick die, BẮT BUỘC:
  1. Kiểm tra bảng `snapshots` trong `tiktok_tracker.db` hoặc cào profile public: Nếu status là `LIVE`, avatar/video còn nguyên -> Nick 100% CÒN SỐNG.
  2. Kiểm tra cột 2FA trong Master DAT: Nếu có Secret Key Base32 -> Nick có 2FA Authenticator.

### Quy tắc 2: Phân loại nguyên nhân ACCOUNT_MISSING đúng trình tự
Khi runner báo `ACCOUNT_MISSING`:
1. **Kiểm tra Viewport / Obfuscation Switcher**: Nick có thể bị đẩy xuống đáy bottom sheet do có nick khác xếp trên, cần vuốt cuộn để thấy.
2. **Kiểm tra Kẹt trần 8 nick vật lý**: Máy đã đạt 8 nick, nick mới reg chèn vào đẩy nick cũ ra khỏi Switcher. Nick cũ không hề die mà chỉ bị logout khỏi app.
3. **Kiểm tra Nick Ký Sinh (Parasite)**: Có nick từ máy khác login nhầm chiếm chỗ. Cần logout nick ký sinh thay vì khai tử nick chính chủ.

## 3. Quy tắc Watchdog / Công cụ Giám sát: ĐÓNG PHIÊN BẮT BUỘC CRONJOB
- Khi phát triển xong công cụ đối soát / cảnh báo (ví dụ `audit_stale_upload_accounts.py`), việc hoàn thành code và unit test **CHƯA ĐỦ**.
- BẮT BUỘC phải tạo và kích hoạt **Cronjob (`hermes cronjob create`)** để scheduler chạy định kỳ tự động và gửi báo cáo Telegram.
- Không có cronjob = tính năng chết im lặng trong ổ cứng.
