# Samsung S7 Android 8 Chrome WebView & Gmail OTP Automation Pitfalls (23/09/2026)

Tài liệu đúc kết thực nghiệm trên farm Samsung Galaxy S7 (Android 8) khi tự động hóa liên kết ChatGPT / đăng ký tài khoản qua Chrome WebView và ứng dụng Gmail:

---

## 1. Cấm Tuyệt Đối `keyevent 111` (ESCAPE) trong Chrome
- **Triệu chứng**: Gửi `keyevent 111` để ẩn bàn phím ảo Samsung.
- **Thực tế**: Trên Chrome Android 8, phím 111 thu nhỏ (minimize) Chrome về màn hình chính Launcher (`com.sec.android.app.launcher`). Tool không còn nhìn thấy trang WebView, dẫn tới timeout `EMAIL_SUBMIT_TIMEOUT` / `OTP_SUBMIT_TIMEOUT`.
- **Khắc phục**: Submit form bằng `keyevent 66` (Enter) hoặc tap trực tiếp tọa độ nút Tiếp tục. Không dùng 111 để ẩn bàn phím trong webview.

---

## 2. Phân Biệt Nút Nổi (FAB) "Soạn thư" vs Màn Hình Soạn Thảo Gmail
- **Triệu chứng**: Check `if "Soạn thư" in xml: press Back` để tránh kẹt bản nháp.
- **Thực tế**: Trên màn hình Hộp thư đến (Inbox) luôn có nút nổi tròn hình dấu cộng (FAB) mang text `"Soạn thư"` (`bounds: [615,1560][1008,1728]`). Check bare text `"Soạn thư"` khiến script hiểu nhầm Inbox là màn hình Compose, liên tục ấn Back làm thoát Gmail ra ngoài.
- **Khắc phục**: Chỉ coi là màn hình Compose khi thấy ID `compose_area`, hoặc đồng thời có `"Đến"` và `"Chủ đề"`, hoặc `"Soạn email"`.

---

## 3. Banner "Đồng bộ ngay" KHÔNG PHẢI Gmail DIE
- **Hiện tượng**: App Gmail hiển thị: *"Tài khoản chưa được đồng bộ hóa... Nhấn Đồng bộ ngay"*.
- **Bản chất**: Tài khoản **LIVE 100%**. Đây là tính năng nhắc bật Master Auto-Sync mặc định của Android khi hệ thống tắt đồng bộ nền để tiết kiệm data/pin trên máy farm.
- **Khắc phục**: Tap nút *"Đồng bộ ngay"* (`bounds [48,924][1032,1073]` -> `540, 998`) hoặc vuốt kéo làm mới màn hình thì thư sẽ về ngay. Dấu hiệu DIE thật sự là thông báo *"Yêu cầu thực hiện hành động trên tài khoản"* (`Account action required`).

---

## 4. Bẫy Luồng Thư Gộp (Thread) & Lỗi OpenAI Rate-Limit `max_check_attempts`
- **Hiện tượng**: Khi gửi lại mã OTP nhiều lần, Gmail gộp tất cả thư OpenAI vào 1 thread hội thoại.
- **Hậu quả**: Quét regex toàn bộ XML sẽ vô tình lấy trúng mã OTP của email cũ nằm ở phần trích dẫn phía dưới thay vì email mới nhất trên đỉnh. Nhập sai OTP 2-3 lần khiến OpenAI kích hoạt rate-limit tạm thời: `error_code: max_check_attempts` (*"Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại"*).
- **Khắc phục**: Duyệt cây UI XML theo thứ tự `root.iter("node")` và chỉ lấy mã xác minh từ **node đầu tiên** có chứa `"tiếp tục:"` hoặc `"mã xác minh"`. Node đầu tiên luôn chứa preview của thư mới nhất.

---

## 5. Cấm Reload URL Đăng Ký Khi Chuyển Tab Về Chrome
- **Hiện tượng**: Ở Step 3, khi chuyển từ Gmail quay lại Chrome, nếu thấy màn hình chưa ở domain OpenAI thì gọi `am start -a ... -d https://chatgpt.com/auth/login?screen_hint=signup`.
- **Hậu quả**: Tải lại URL sẽ hủy form nhập OTP đang mở sẵn và làm OpenAI báo: *"Phiên của bạn đã kết thúc"*.
- **Khắc phục**: Chỉ đưa Chrome lên foreground bằng `am start -n com.android.chrome/org.chromium.chrome.browser.ChromeTabbedActivity` hoặc `keyevent 4 (Back)` để quay lại đúng tab đang chờ mã.
