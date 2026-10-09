# ChatGPT Linking & Registration Pitfalls on Android 8 (Samsung Galaxy S7) — 2026-09-24

## 1. Gmail Thread Grouping & Auto-Sync Off -> Stale OTP & `max_check_attempts`

### Triệu chứng & Hậu quả
- Chuỗi liên kết ChatGPT thất bại hàng loạt (0/8 fail) dù Gmail reg thành công và LIVE 100%.
- Màn hình OpenAI báo lỗi đỏ: `error_code: max_check_attempts` ("Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại"). Phiên đăng ký bị đóng băng 15–30 phút.

### Nguyên nhân kỹ thuật
- App Gmail tự động gom toàn bộ email từ OpenAI vào 1 luồng hội thoại (`thread`).
- Tính năng `Auto-sync` trên điện thoại Farm mặc định bị TẮT để tiết kiệm tài nguyên mạng/pin. Khi mở Gmail, thư mới không tự nhảy ra ngoài Inbox ngay.
- Script dùng regex phẳng quét toàn bộ XML thô nên vô tình bốc mã OTP của **bức thư cũ** (từ ngày hôm trước hoặc mã đã hết hạn). Nhập mã cũ 3 lần vào form OpenAI sẽ kích hoạt cơ chế chống brute-force `max_check_attempts`.

### Giải pháp chuẩn
1. Kéo vuốt làm mới Inbox ở vùng an toàn không vướng banner:
   ```python
   shell(device_id, "input", "swipe", "540", "1350", "540", "1800", "400")
   time.sleep(2.5)
   ```
2. Parse XML theo thứ tự cây từ trên xuống (`xml.etree.ElementTree`), lấy OTP ở node email xuất hiện đầu tiên trên đỉnh Inbox.
3. Nếu thư bị gom trong thread: tap vào thread `(540, 1420)` để mở nội dung và lấy mã mới nhất trên cùng.

---

## 2. Chính sách mật khẩu mới của OpenAI (Bắt buộc >= 12 ký tự)

### Triệu chứng & Hậu quả
- Sau khi nhập OTP hoặc chọn "Tiếp tục với mật khẩu", OpenAI chuyển sang màn hình `Tạo mật khẩu`.
- Nút "Tiếp tục" bị mờ, màn hình báo đỏ: `X Ít nhất 12 ký tự`. Script kẹt timeout vì không bấm được Tiếp tục.

### Nguyên nhân kỹ thuật
- OpenAI nâng chuẩn bảo mật yêu cầu mật khẩu đăng ký tối thiểu **12 ký tự**.
- Mật khẩu tạo Gmail tự động của Farm thường có độ dài 10–11 ký tự (ví dụ: `Dao$Zone608` = 11 ký tự, `Win44@Tra7` = 10 ký tự).

### Giải pháp chuẩn
- Tự động kiểm tra và pad mật khẩu đạt tối thiểu 12 ký tự trước khi submit:
  ```python
  password_clean = password or "Password123@Aa"
  if len(password_clean) < 12:
      password_clean = f"{password_clean}@2026"
  ```
- Thêm khối nhận diện màn hình `Tạo mật khẩu`:
  - Input mật khẩu vào ô `(540, 1328)`.
  - Gửi `keyevent 4` để ẩn bàn phím ảo.
  - Tap nút "Tiếp tục" ở tọa độ `(540, 1814)`.
  - Gửi thêm `keyevent 4` để đóng popup gợi ý "Lưu mật khẩu vào Google" của Chrome nếu có.

---

## 3. Bàn phím ảo Samsung S7 làm xô lệch layout & tap trúng phím `g`

### Triệu chứng & Hậu quả
- Email trong ô nhập bị biến dạng thành `@gmail.comg`. Form web báo lỗi địa chỉ email không hợp lệ và không thể submit.

### Nguyên nhân kỹ thuật
- Khi focus vào ô input email, bàn phím ảo Samsung mở lên đẩy nút "Tiếp tục" của webview từ dưới lên tọa độ `(540, 762)`.
- Tọa độ cũ `(540, 1504)` nằm đúng vị trí của phím chữ **`g`** trên bàn phím ảo Samsung. Tap vào đó sẽ gõ thêm ký tự `g` vào cuối email.

### Giải pháp chuẩn
- Không tap tọa độ dưới màn hình khi bàn phím đang mở.
- Sau khi gõ email bằng `input text`, tap thẳng vào vị trí nút bị đẩy lên `(540, 762)` và gửi phím Enter:
  ```python
  shell(device_id, "input", "text", email_clean)
  time.sleep(0.5)
  tap(device_id, 540, 762, wait=1.0)
  shell(device_id, "input", "keyevent", "66")
  ```

---

## 4. Bẫy nút FAB "Soạn thư" & kẹt Search Mode trong Gmail

### Triệu chứng & Hậu quả
- Vừa mở Gmail thì app tự động bấm Back văng ngược lại Chrome hoặc kẹt ở ô tìm kiếm với bàn phím che kín màn hình, timeout 90s không đọc được thư.

### Nguyên nhân kỹ thuật
- Nút nổi tạo thư mới (FAB) ở góc phải Inbox của app Gmail có content-desc là `"Soạn thư"`. Điều kiện cũ `if "Soạn thư" in xml: press Back` bắt nhầm nút này và tự thoát khỏi Gmail.
- Khi Gmail bị dính vào ô tìm kiếm ("Tìm kiếm trong thư"), 1 lần Back chỉ ẩn bàn phím chứ chưa thoát về Inbox.

### Giải pháp chuẩn
1. Nhận diện màn hình Soạn thư thật sự bằng `compose_area` hoặc `("Chủ đề" in xml and "Đến" in xml)`, tuyệt đối KHÔNG check từ khóa `"Soạn thư"`.
2. Thoát Search mode bằng 2 lần phím Back liên tiếp:
   ```python
   if any(k in xml for k in ["Tệp đính kèm", "Xoá văn bản", "Tìm kiếm trong thư"]):
       shell(device_id, "input", "keyevent", "4")
       time.sleep(0.5)
       shell(device_id, "input", "keyevent", "4")
       time.sleep(1.5)
   ```
