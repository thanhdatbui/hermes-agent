# Strict Profile Isolation & Checkpoint Triage Rules

## 1. Lỗi Chí Mạng: Dùng Chung Profile GPM Cho Nhiều Gmail (Profile Cross-Contamination)
- **Triệu chứng**: Khi đăng nhập hoặc OAuth, trình duyệt Playwright mở profile GPM đã mang session/cookie của Gmail A để đăng nhập Gmail B.
- **Hậu quả**: Google phát hiện cookie xung đột giữa 2 tài khoản trên cùng User Data Dir, kích hoạt ngay lập tức **Hard SMS Checkpoint** ("Có điều bất thường về hoạt động của bạn..."), làm hỏng phiên và dính cờ bot cả 2 tài khoản.
- **Nguyên nhân gốc rễ trong code**:
  Code phân giải profile kiểm tra `if os.path.exists(prof_dir)` trước khi query DB theo email. Nếu script batch truyền nhầm profile path của máy cũ (ví dụ: `SUNVqFew4a-05092026` của M61 vốn thuộc về `khahoan240161`) hoặc thư mục `M57 - 5123 - phammai18052001@gmail.com`, code thấy thư mục đó tồn tại trên đĩa nên **nhảy thẳng vào dùng luôn mà không kiểm tra xem profile đó thuộc về ai**.

### Quy Tắc Bất Biến (Strict 1 Profile : 1 Gmail Guard):
1. **Luôn query `profile_data.db` theo chính xác email (`lower(Name) LIKE %email%`) trước tiên**. Nếu tìm thấy ProfilePath và thư mục tồn tại, chỉ dùng profile đó.
2. **Cross-account Collision Guard**:
   - Nếu `acc['profile']` chứa ký tự `@` nhưng khác email hiện tại -> BÁO LỖI VÀ CHẶN NGAY.
   - Nếu tra trong `profile_data.db` thấy `ProfilePath = acc['profile']` đang thuộc sở hữu của một email khác -> BÁO LỖI VÀ CHẶN NGAY (`BLOCKED_PROFILE_COLLISION`).
3. **CẤM TUYỆT ĐỐI** fallback mở profile của account khác hoặc dùng profile dùng chung theo số máy nếu trong đó đã có tài khoản Google khác đăng nhập. Nếu không tìm thấy profile riêng, trả về `PROFILE_NOT_FOUND` để tạo profile mới độc lập.

---

## 2. Quy Tắc Đối Soát: Đã Có OAuth Antigravity Thì Tuyệt Đối Không Kết Luận "Thiếu Profile"
- Mọi tài khoản đã từng cấp quyền OAuth Antigravity thành công trên OmniRoute đều được thực hiện qua GPM Playwright hot-session.
- Trước khi kết luận tài khoản "không có profile" hay "bị xóa profile":
  1. Tra cứu file log lịch sử (`run_batch_*.log`, `batch_2fa_run.log`).
  2. Tra cứu `oauth_pipeline_status.json` xem mã connection ID và port nạp thành công.
  3. Kiểm tra danh sách thư mục thực tế trên đĩa `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\`. Một số profile có thể đang mang tên máy (ví dụ `M61 - 5127 - ...`) dùng chung cho đợt nạp trước.
  4. Tránh kết luận vội vàng "thiếu profile" gây hoang mang và phán đoán sai lệch.

---

## 3. Triage: Phân Biệt Hard SMS Checkpoint vs S7 Google Prompt
- **Hard SMS Checkpoint (Google cờ đỏ trên Web)**:
  - Dấu hiệu trên màn hình Web: *"Có điều bất thường về hoạt động của bạn... Nhập số điện thoại để nhận tin nhắn văn bản"* hoặc *"Đã xảy ra lỗi. Rất tiếc, đã xảy ra sự cố. Vui lòng thử lại"*, hoặc chọn SMS gửi về SĐT khôi phục cũ.
  - **Bản chất**: Google chặn trực tiếp trên browser session do IP/proxy hoặc cookie xung đột. **GOOGLE HOÀN TOÀN KHÔNG BẮN PROMPT VỀ SAMSUNG S7**.
  - **Hành động đúng**: BẮT BUỘC dừng luồng ngay, cho tài khoản và proxy ngâm nghỉ (cooling). CẤM retry liên tục làm cháy acc.
- **S7 Google Prompt (Xác minh thiết bị tin cậy)**:
  - Dấu hiệu trên màn hình Web: *"Kiểm tra điện thoại của bạn"*, *"Nhấn vào Có trên điện thoại của bạn"*, hoặc hiện số PIN 2 số (ví dụ: 58, 91).
  - **Bản chất**: Thiết bị Samsung S7 nhận được thông báo từ Google Play Services, script ATX/ADB trên S7 có thể tap "Có" và chọn đúng số PIN để hoàn tất duyệt.
