# Google Hard Phone Checkpoint (challenge/iap) & Anti-Spam Breaker

## 1. Hiện tượng & Nhận diện
- **URL**: `accounts.google.com/v3/signin/challenge/iap...`
- **Nội dung hiển thị**:
  - Tiêu đề: "Xác minh danh tính của bạn" (Verify your identity).
  - Lý do: "Có điều bất thường về hoạt động của bạn. Để bảo mật tài khoản của bạn, Google muốn đảm bảo rằng người đăng nhập chính là bạn."
  - Yêu cầu: "Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh" kèm ô chọn quốc gia (cờ Mỹ 🇺🇸) và ô nhập `input[type="tel"]` / `input#phoneNumberId`.
  - Nút: Có thể có link/nút "Thử cách khác" (Try another way) hoặc chỉ có nút "Tiếp theo".

## 2. Pitfall chí mạng: Vòng lặp spam "Thử cách khác" vô tận
- Google đưa ra màn hình này khi phát hiện rủi ro cao (IP lạ, fingerprint proxy bất thường).
- Khi script click nút "Thử cách khác", Google thường **không cấp phương thức bypass nào khác** (không có Google Prompt, không có TOTP/Authenticator, không có mã 10 số OOTP), mà chỉ tải lại chính trang `challenge/iap`.
- Nếu script không có biến đếm số lần thử và điều kiện dừng, script sẽ click nút "Thử cách khác" lặp đi lặp lại liên tục cho đến khi cạn timeout 180s. Điều này làm tài khoản bị Google đánh cờ spam, khóa tạm thời hoặc văng hoàn toàn.

## 3. Quy tắc xử lý chuẩn (Fail-Fast & Hard Breaker)
1. **Giới hạn số lần bấm "Thử cách khác"**: Tối đa **1 lần duy nhất** (`try_another_phone_count <= 1`).
2. **Fail-Fast ngay lập tức**:
   - Nếu không có nút "Thử cách khác" $\rightarrow$ Dừng ngay (`status: PHONE_CHECKPOINT`), chụp ảnh hiện trường debug.
   - Nếu đã bấm "Thử cách khác" 1 lần mà trang vẫn giữ nguyên `challenge/iap` hoặc nội dung yêu cầu SĐT $\rightarrow$ DỪNG NGAY LẬP TỨC (ABORT). Cấm tiếp tục bấm thử.
3. **Cảnh giác match nhầm ô số điện thoại Tad**:
   - Tuyệt đối không kiểm tra lỏng lẻo kiểu `if "nhận mã xác minh" in b_txt:` vì màn hình `challenge/iap` luôn chứa câu: *"để nhận tin nhắn văn bản cùng mã xác minh"*.
   - Chỉ điền số Tad `0906746624` khi Google yêu cầu xác nhận số điện thoại đã lưu có đuôi 24 (`"24"` đi kèm `"xác nhận số điện thoại"` / `"••"` / `"đuôi"` / `"số điện thoại bạn đã thêm"`).
