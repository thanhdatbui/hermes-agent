# CẤM ĐÁNH ĐỒNG GMAIL DIE VỚI TIKTOK DIE — NGUYÊN TẮC BẢO TỒN TÀI SẢN NICK 2FA TOTP

## 1. Bản chất sự cố & Bài học xương máu (Incident 10/10/2026)
- **Hiện tượng**: Nick `@anhdo829` (7 tháng tuổi, 21 video, 116 follow, 428 tim) trên Máy 20 có liên kết với Gmail `dotranganh221220002212@gmail.com`. Mail này bị Google khóa ngày 19/09 và ghi nhận vào `gmail_die_tong.txt`.
- **Sai lầm chết người của Agent**: Khi Máy 20 báo lỗi `ACCOUNT_MISSING`, agent tra cứu thấy Gmail nằm trong `gmail_die_tong.txt` liền vội vàng phán bừa là "nick TikTok đã die", rồi tự ý thay thế nick mới và khai tử nick cũ trên Master Excel.
- **Sự thật**: 
  - Nick TikTok `@anhdo829` VẪN ĐANG HOẠT ĐỘNG HOÀN TOÀN BÌNH THƯỜNG (Public snapshot vẫn LIVE 100%).
  - Nick đã được kích hoạt **2FA Ứng dụng xác thực (TOTP)** với Secret Key lưu trong Master Excel.
  - Khi đăng nhập TikTok, hệ thống chỉ cần: `Username` + `Password` + `Mã TOTP 6 số sinh từ Secret Key` -> **HOÀN TOÀN KHÔNG CẦN OTP GMAIL**.

## 2. Quy tắc Bất biến (Hard Invariants)

### INVARIANT 1: CẤM TUYỆT ĐỐI ĐÁNH ĐỒNG "GMAIL DIE = TIKTOK DIE"
- Trạng thái của Gmail và trạng thái của TikTok là **hoàn toàn độc lập** sau khi nick đã tạo và bật bảo mật.
- Việc Gmail bị Google vô hiệu hóa **KHÔNG ĐƯỢC PHÉP** dùng làm căn cứ để kết luận nick TikTok die hay loại bỏ nick khỏi Farm.

### INVARIANT 2: TRÌNH TỰ KIỂM TRA TRƯỚC KHI KHAI TỬ HOẶC THAY THẾ NICK
Trước khi đề xuất hoặc thực hiện thay thế bất kỳ tài khoản TikTok nào vì nghi ngờ "die", Coordinator/Worker BẮT BUỘC phải thực hiện đủ 3 bước kiểm tra:
1. **Kiểm tra Public Snapshot / Tracker (`snapshots` table)**:
   - Tra cứu trong `tiktok_tracker.db`: Nick có đang mang trạng thái `LIVE` không?
   - Cào thử public profile: Nếu profile vẫn tồn tại, avatar hiển thị, video vẫn xem được -> Nick 100% CÒN SỐNG.
2. **Kiểm tra 2FA Authenticator (Cột 2FA trong Master DAT)**:
   - Nếu có Secret Key 32 ký tự (Base32) -> Nick đăng nhập bằng TOTP, bypass hoàn toàn Gmail live check.
3. **Chỉ khai tử khi và chỉ khi**:
   - Public profile trả về `User not found` / `Account banned` / `Account suspended` trên TikTok.
   - HOẶC khi đăng nhập bằng Username/Pass/2FA mà TikTok báo rõ ràng: `Tài khoản đã bị cấm vĩnh viễn`.

## 3. Quy trình khôi phục & nạp lại nick 2FA có mail die
1. Giữ nguyên credential trong Master DAT (`taikhoan_dat_v2_updated .xlsx`).
2. Nếu máy bị đầy 8 nick, xác định nick non/ký sinh cần logout.
3. Chạy `tiktok_login_v1.py <STT> --email <ID_TIKTOK>`: Script đã tích hợp cờ `bypass_2fa_auth`, tự động sinh mã TOTP 6 số và đăng nhập mượt mà.
4. Sau khi vào app an toàn, có thể liên kết bổ sung Hotmail/Gmail live mới nếu cần đổi mật khẩu.
