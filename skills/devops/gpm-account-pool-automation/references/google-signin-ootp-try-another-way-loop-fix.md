# Google Sign-in Challenge Loop Prevention & 2SV Re-Auth Handling

## 1. Cạm bẫy từ khóa "Xác minh danh tính" & Vòng lặp Try Another Way vô tận

### Triệu chứng
Script tự động đăng nhập Google bị kẹt 15/15 bước tại các URL `challenge/selection` hoặc `challenge/ootp` (nhập mã bảo mật 10 số từ Android Settings). Script liên tục bấm "Thử cách khác" (Try another way), khiến trang bị lặp qua lại giữa selection và ootp mà không bao giờ điền mã.

### Nguyên nhân cốt lõi
1. **Bẫy text tiêu đề Google:** Google render dòng chữ `"Xác minh danh tính của bạn Để giữ an toàn..."` trên **tiêu đề của tất cả** các trang xác minh (`challenge/selection`, `challenge/ootp`, `challenge/pwd`).
2. **Kiểm tra lỏng lẻo:** Nếu script có điều kiện:
   ```python
   # NGUY HIỂM - GÂY VÒNG LẶP VÔ HẠN
   if "challenge/dp" in current_url or any(kw in body_text for kw in [..., "xác minh danh tính"]):
       click("Thử cách khác")
   ```
   Trang `challenge/ootp` và `challenge/selection` đều thỏa mãn điều kiện này, và ở chân trang luôn có nút/link "Thử cách khác". Script sẽ click nút này làm Google quay ngược lại menu chọn, không bao giờ tới khối nhập mã.
3. **Nghịch đảo thứ tự kiểm tra:** Đặt khối "Thử cách khác" TRƯỚC khối kiểm tra ô nhập mã `code_inp` và lựa chọn `sec_opt` / `rec_opt`.

### Cách khắc phục chuẩn
- **TUYỆT ĐỐI KHÔNG** dùng từ khóa `"xác minh danh tính"` để kích hoạt "Thử cách khác".
- Chỉ bấm "Thử cách khác" khi URL chứa `"challenge/dp"` HOẶC body chứa cụm từ thông báo nhắc điện thoại cụ thể:
  `["kiểm tra điện thoại", "check your phone", "tap yes", "chạm vào có", "xác nhận trên điện thoại"]`.
- **ĐẢO VỊ TRÍ:** BẮT BUỘC kiểm tra ô nhập mã (`code_inp`, `challenge/ootp`) và các tùy chọn (`sec_opt`, `rec_opt`) **TRƯỚC** khối "Thử cách khác".

---

## 2. Xử lý Identity Re-Auth (`challenge/dp`) khi Bật 2SV Authenticator

### Vấn đề
Khi tài khoản đã đăng nhập vào `myaccount.google.com` và điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator`, Google thường yêu cầu xác thực lại danh tính (Step-up / Re-authentication).
Không chỉ có mật khẩu (`challenge/pwd`) hay reCAPTCHA (`challenge/recaptcha`), Google còn có thể đẩy trực tiếp Google Prompt (`challenge/dp`).

### Giải pháp
Trong vòng lặp chờ trang Authenticator (tối thiểu 15 bước, không dùng 5 bước):
1. Bắt `challenge/pwd` -> điền mật khẩu -> Enter.
2. Bắt `challenge/recaptcha` -> giải audio challenge.
3. Bắt `code_inp` trên `challenge/ootp` -> lấy mã bảo mật S7 qua `get_s7_security_code` -> điền và submit.
4. Bắt `challenge/selection` -> ưu tiên click Recovery Email (nếu là `thanhdatbui1995`) hoặc Security Code S7 (`sec_opt`).
5. Bắt `challenge/dp` -> click "Thử cách khác" -> chuyển sang `challenge/selection`.
6. Quét và dismiss onboarding popups ("Để sau", "Bỏ qua", "Hủy", "Not now").
7. Chỉ thoát loop khi URL chứa `two-step-verification/authenticator` và KHÔNG còn chuỗi `challenge` hay `signin`.

---

## 3. Kỷ luật Đánh thức & Mở khóa Samsung S7 (Tránh Tắt Màn Hình Oan)

### Cạm bẫy `keyevent 26` (Power)
`input keyevent 26` là nút nguồn vật lý (Power toggle). Nếu màn hình S7 đang BẬT, gửi `keyevent 26` sẽ làm TẮT và KHÓA màn hình! Khi đó các lệnh tap/dump hierarchy sau đó đều rơi vào Lock Screen.

### Quy tắc mở khóa an toàn
- Dùng `input keyevent 82` (Menu / Unlock key) để đánh thức và mở khóa mà không làm tắt màn hình nếu đang sáng.
- Vuốt mở khóa theo đúng độ phân giải thiết bị (ví dụ S7 1080x1920: `input swipe 500 1000 500 200`).
- Khởi chạy trực tiếp intent: `am start -n com.google.android.gms/.app.settings.GoogleSettingsLink`.
