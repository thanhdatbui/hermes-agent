# Pitfalls Phối Hợp GPM ↔ Galaxy S7 Duyệt Google Prompt ("Nhấn Có") & Checkpoint Thực Tế

## 1. Màn Hình Menu Chọn Phương Thức ("Chọn cách bạn muốn đăng nhập")
- **Hiện tượng**: Khi đăng nhập Google trên GPM Browser, Google không nhảy thẳng vào màn hình mã PIN hoặc push notification (`challenge/dp`) mà hiển thị menu dạng danh sách:
  * *"Nhấn vào Có trên điện thoại hoặc máy tính bảng"*
  * *"Sử dụng điện thoại hoặc máy tính bảng của bạn để nhận mã bảo mật"*
  * *"Thử cách khác"*
- **Bẫy code (Race / False Positive)**:
  * Nếu matcher kiểm tra chuỗi chung như `"nhấn vào có" in body_content` rồi lập tức coi là đã ở màn hình `challenge/dp`, code sẽ gọi hàm duyệt S7 (`approve_s7_google_prompt`) ngay lập tức.
  * **Hậu quả**: Trên thực tế, trên trình duyệt PC, Google CHƯA gửi push notification sang S7 vì người dùng chưa click chọn mục *"Nhấn vào Có..."*. S7 không hề nhận được bất kỳ thông báo nào, dẫn đến việc script đợi trên S7 15-20s rồi timeout/thất bại.
- **Quy tắc xử lý**:
  * Phải click vào phần tử `div[role="link"]` hoặc `li` chứa text *"Nhấn vào Có"* trên trang chọn phương thức trước.
  * Sau khi click, đợi trang điều hướng sang `challenge/dp` (hoặc xuất hiện thông báo *"Kiểm tra điện thoại..."* và mã PIN 2 số trên PC) thì MỚI bắt đầu kích hoạt luồng ADB/ATX trên điện thoại S7 để kéo thanh thông báo và duyệt.

---

## 2. Rớt Kết Nối ADB Trên Thiết Bị Tin Cậy Bậc 1 (S7 Offline)
- **Hiện tượng**: GPM đã vào màn hình prompt hoặc code chuẩn bị duyệt S7, nhưng S7 không phản hồi hoặc lệnh forward port 7912 thất bại.
- **Nguyên nhân hiện trường**:
  * Cáp kết nối USB bị lỏng, driver ADB bị drop hoặc thiết bị S7 chuyển sang trạng thái `offline` / biến mất khỏi `adb devices`.
- **Quy tắc phòng thủ**:
  * Trước khi vào luồng chờ prompt, BẮT BUỘC kiểm tra `adb devices` xem serial của máy đó (ví dụ Máy 30: `ce0217126cd4bc640c`) có đang ở trạng thái `device` hay không.
  * Nếu thiết bị offline, ghi log cảnh báo thiết bị mất kết nối ADB và chuyển hướng sang phương thức dự phòng (hoặc abort an toàn), tránh ngồi chờ 180s gây timeout vô ích.

---

## 3. Hard Phone Checkpoint Thay Vì Google Prompt
- **Hiện tượng**: Thay vì hiển thị tùy chọn gửi xác minh về điện thoại S7 đã liên kết, Google lập tức chặn cứng bằng thông báo:
  > *"Có điều bất thường về hoạt động của bạn. Để bảo mật tài khoản của bạn, Google muốn đảm bảo rằng người đăng nhập chính là bạn... Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh..."*
- **Bản chất**:
  * Google đã cắm cờ bất thường trên IP (proxy) hoặc profile browser.
  * Trong trường hợp này, Google **hoàn toàn KHÔNG cung cấp tùy chọn push notification về S7** hay nhận Security Code, mà ép buộc cung cấp một số điện thoại mới chưa bị cắm cờ để nhận SMS giải checkpoint.
- **Quy tắc phòng thủ**:
  * Nhận diện bằng WinRT OCR hoặc DOM (`challenge/iap`, *"có điều bất thường về hoạt động của bạn"*).
  * Thử click nút *"Thử cách khác"* tối đa 1 lần. Nếu không có hoặc sau khi click vẫn quay lại form nhập SĐT mới: DỪNG NGAY (Abort), ghi nhận `PHONE_CHECKPOINT` và ngắt quy trình, tuyệt đối không spam thử lại để tránh làm hỏng tài khoản.
