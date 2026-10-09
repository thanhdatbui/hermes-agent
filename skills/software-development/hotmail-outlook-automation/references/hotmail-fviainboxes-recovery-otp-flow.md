# Hotmail Identity Verification & fviainboxes.com OTP Automation Flow

## 1. Bối cảnh & Triệu chứng Checkpoint
Khi điều hướng tới `https://account.live.com/password/change` trên GPM Profile, Microsoft thường kích hoạt màn hình xác minh danh tính (Proof Challenge):
- Tiêu đề: "Sắp hoàn thành / Chỉ còn một bước để xác minh danh tính của bạn" hoặc "Xác minh email của bạn".
- Phương thức hiển thị: "Gửi mã đến vi*****@fviainboxes.com" (hoặc domain mail khôi phục khác).
- **Yêu cầu của Microsoft:** Bắt buộc nhập lại ĐẦY ĐỦ địa chỉ email khôi phục gốc vào ô xác nhận trước khi nút "Gửi mã" hoạt động.

## 2. Nguồn dữ liệu Email khôi phục
- Địa chỉ mail khôi phục gốc được lưu tại Cột 5 (`mail khôi phục`) trong file Excel `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- Ví dụ: `vistemeggett3761@hotmail.com` có mail khôi phục tương ứng là `vistemeggett3761iro7@fviainboxes.com`.

## 3. Giao diện Form Xác Minh & Playwright Selectors
Microsoft hiện có 2 phiên bản giao diện:
### UI Mới (Fluent Design 2026):
- Ô nhập email khôi phục xác nhận: `#proof-confirmation-email-input` (type text).
- Nút gửi mã: `button:has-text('Gửi mã')` hoặc `button:has-text('Send code')`.
- Nhập OTP: **6 ô riêng biệt** có id `#codeEntry-0`, `#codeEntry-1`, ..., `#codeEntry-5`.
  - Cần fill từng ký tự `otp_code[i]` vào từng ô `#codeEntry-{i}` với `time.sleep(0.2)`.

### UI Cũ:
- Chọn proof: `text='fviainboxes'` hoặc `text='Email'`.
- Ô nhập email xác nhận: `#iProofEmail`.
- Nút gửi mã: `#iSelectProofAction` hoặc `input[type='submit']`.
- Nhập OTP: 1 ô duy nhất `#iOttText` (hoặc `input[name='otc']`).
- Nút xác nhận OTP: `#idSIButton9` hoặc `#iSubmitProofAction`.

## 4. API Lấy Mã OTP từ fviainboxes.com
API web công khai của `fviainboxes.com` (tuyệt đối không kết luận mail ảo rác không vào được):
1. **Lấy danh sách thư:**
   ```http
   GET https://fviainboxes.com/messages?username={username}&domain=fviainboxes.com
   Headers: User-Agent: Mozilla/5.0
   ```
   JSON trả về: `{"result": [{"id": "...", "subject": "Personal Microsoft account security code", "createdAt": ...}]}`.
2. **Đọc nội dung thư:**
   ```http
   GET https://fviainboxes.com/message?username={username}&domain=fviainboxes.com&id={msg_id}
   ```
3. **Regex trích xuất mã OTP Microsoft (6 hoặc 7 số):**
   - Nội dung thư thường có dạng:
     - `Your single-use code is: 483805`
     - Hoặc HTML: `Security code: <span ...>534210</span>`
   - Cần decode chuỗi JSON escapse nếu có (`json.loads(raw_data)`).
   - **Bắt buộc lọc bỏ false-positives:** Loại trừ các mã số hệ thống cố định trong template email của Microsoft như `707070` (màu hex text `#707070`) và `521839` (LinkId Privacy Statement).

## 5. Màn hình Chuyển tiếp (Interstitials) trước khi vào Form Đổi Pass
Sau khi xác minh OTP thành công, Microsoft thường chuyển hướng qua các màn hình phụ:
1. **Cập nhật điều khoản:** "Chúng tôi đang cập nhật các điều khoản của mình" -> Bấm nút `button:has-text('Tiếp theo')` hoặc `#iNext`.
2. **Duy trì đăng nhập? (KMSI):** "Stay signed in?" -> Bấm `button:has-text('Có')` hoặc `#idSIButton9` để ghi nhận và duy trì session trên GPM profile.
3. **Form đổi mật khẩu:**
   - Trường hợp đã xác minh qua Proof OTP: Trường `#currentPassword` thường bị ẩn/bỏ qua!
   - Chỉ xuất hiện 2 ô: `#iPassword` (Mật khẩu mới) và `#iRetypePassword` (Nhập lại mật khẩu).
   - Nút Submit: `#UpdatePasswordAction` (type submit) hoặc nút `Lưu` / `#save`.
