# TikTok Identity Verification Pitfalls & 2FA Enforcement Rules

## 1. Bản chất cơ chế bảo mật "Xác minh danh tính" (Verify Identity) của TikTok
- **Sự cố thực tế:** Khi tài khoản đang đăng nhập trong app TikTok vào mục *Thông tin tài khoản* -> *Email* -> *Thay đổi email*, TikTok có thể bật popup chắn toàn màn hình:
  - Header: `Xác minh danh tính` (`Verify identity`)
  - Subtext: `Trước khi tiếp tục, hãy xác minh danh tính của bạn bằng một trong các phương pháp sau đây.`
- **Bẫy hiểu nhầm 2FA TOTP:**
  - **Tài khoản dù đã bật 2FA TOTP (Authenticator App) trong hệ thống/cơ sở dữ liệu, TikTok VẪN KHÔNG ĐƯA RA LỰA CHỌN NHẬP TOTP TRÊN FORM NÀY.**
  - Lý do: 2FA TOTP chỉ dùng khi login thiết bị mới (`Xác minh 2 bước`). Khi đổi thông tin nhạy cảm (Email/Password), TikTok áp dụng chính sách *Xác minh danh tính* riêng biệt, ưu tiên bắt gửi OTP về **chính Email cũ đang liên kết**.

## 2. Phân loại 2 dạng màn hình Xác minh danh tính
1. **Dạng 1 (Chỉ có gửi mã về Email cũ):**
   - Màn hình chỉ có 1 lựa chọn radio: `<email_cũ>@gmail.com`.
   - Phía dưới chỉ có nút `Tiếp` và link `Yêu cầu hỗ trợ` (dẫn sang ticket TikTok Support).
   - **Xử lý:** Đây là ngõ cụt nếu Email cũ đã DIE hoàn toàn không nhận được thư. Worker bắt buộc phát hiện cụm `xác minh danh tính` / `xác minh để là bạn` và **DỪNG NGAY / SKIP AN TOÀN**, không được cố chấp đi tiếp lấy OTP Hotmail mới rồi báo lỗi `khong lay duoc OTP` làm kẹt hàng trăm vòng lặp.
2. **Dạng 2 (Có lựa chọn Mật khẩu):**
   - Màn hình có lựa chọn radio `Mật khẩu` (`Måt khäU`).
   - **Xử lý:**
     + Tap radio button chọn `Mật khẩu` (khoảng `x=120, y=680` hoặc parse OCR node `Mật khẩu`).
     + Tap nút `Tiếp` (`x=540, y=1700`).
     + Điền mật khẩu TikTok của nick (lấy từ SSOT `farm_master.db` hoặc `taikhoan_dat_v2_updated .xlsx`).
     + Bấm xác nhận để mở khóa form điền email mới.

## 3. Popup xác nhận 2 lớp "Thay đổi email?"
- Khi tap vào dòng `Email` trong *Thông tin tài khoản*, TikTok mở modal chọn:
  - `Thay đổi email` (nút trên)
  - `Hủy liên kết email` (nút dưới)
- Sau khi bấm `Thay đổi email`, TikTok hiển thị tiếp popup xác nhận:
  - Tiêu đề: `Thay đổi email?`
  - Nội dung: *"Email mới của bạn cũng sẽ được dùng cho xác minh 2 bước."*
  - 2 nút lựa chọn: `Quay lại` (trái) và `Tiếp tục` / OCR: `Tiép tvc` (phải, bounds `[651, 1286, 849, 1339]`, tâm tap `[750, 1285]`).
- **Cạm bẫy:** Bắt buộc phải phát hiện modal này và tap `Tiếp tục` để mở form nhập mail mới. Nếu không tap, app kẹt ở modal cũ, các lệnh tap ô input mail tiếp theo sẽ bị trượt vào form chọn quốc gia.

## 4. Khắc phục lỗi Pool Hotmail Token Grant Expired (`AADSTS70000`)
- **Triệu chứng:** Graph API trả về `HTTP Error 400: Bad Request` kèm body:
  `{"error":"invalid_grant","error_description":"AADSTS70000: The user could not be authenticated as the grant is expired."}`.
- **Bẫy:** Nếu không xử lý exception này, worker bốc phải mail bị hết hạn grant sẽ crash hoặc kẹt vòng lặp lấy OTP.
- **Giải pháp:**
  - Bắt buộc kiểm tra `refresh_token` qua endpoint token Microsoft trước khi nạp vào form TikTok.
  - Nếu gặp `AADSTS70000`: Đánh dấu `oauth_status = 'EXPIRED'` trong database và tự động fallback lấy mail sạch tiếp theo, không được dùng mail lỗi.

## 5. Fuzzy Matching Tên Nick Trong Switcher (Chống Lỗi Nhầm Ký Tự OCR)
- Trên Samsung S7, WinRT OCR thường đọc nhầm:
  - Chữ `l` (thường) thành `I` (hoa) hoặc số `1` (ví dụ: `phungloan0138` -> `phungIoan0138`, `l.thanh.ngn311` -> `I.thanh.ngn311`).
  - Dấu chấm `.` hoặc gạch dưới `_` bị bỏ sót hoặc nhận diện thành khoảng trắng.
- **Quy chuẩn Matching bắt buộc:**
  ```python
  def norm_name(s):
      return s.lower().replace('l', 'i').replace('1', 'i').replace('.', '').replace('_', '').strip()

  u_norm = norm_name(username)
  for text_item, bounds in sw_boxes:
      t_norm = norm_name(text_item)
      if username.lower() in text_item.lower() or u_norm in t_norm:
          # Match thành công
  ```
