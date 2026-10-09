# Samsung S7 (Android 8) ChatGPT Registration Pitfalls & Runbook (23/09/2026)

Tài liệu đúc kết các bẫy thực địa khi liên kết / đăng ký tài khoản ChatGPT tự động qua Gmail trên thiết bị Samsung Galaxy S7 (Android 8) trong repo `D:/Taadaa/register gmail/scripts/hook_chatgpt_register.py`.

---

## 1. Bẫy Keyevent 111 (ESCAPE) trên Chrome Android 8
- **Hiện tượng**: Gọi `shell(device_id, "input", "keyevent", "111")` để ẩn bàn phím ảo Samsung.
- **Hậu quả**: Trên Samsung Galaxy S7 (Android 8), phím `111` trong Chrome đóng vai trò phím thoát, khiến Chrome bị thu nhỏ (minimize) hoặc văng thẳng về màn hình chính Launcher (`com.sec.android.app.launcher`). Tool không còn thấy trang WebView của ChatGPT, dẫn tới kẹt timeout (`EMAIL_SUBMIT_TIMEOUT` / `OTP_SUBMIT_TIMEOUT`).
- **Khắc phục**: Tuyệt đối **CẤM** dùng `keyevent 111` trong Chrome. Submit form webview bằng phím `Enter (keyevent 66)` hoặc click thẳng vào toạ độ nút Submit/Tiếp tục.

---

## 2. Bẫy Nút Nổi (FAB) "Soạn thư" vs Màn hình Soạn thư trong Gmail
- **Hiện tượng**: Kiểm tra `if "Soạn thư" in xml: press Back` để thoát màn hình soạn thảo bản nháp nếu vô tình tap nhầm.
- **Hậu quả**: Trên màn hình Hộp thư đến (Inbox) mặc định của Gmail luôn có nút nổi (Floating Action Button) mang text/content-desc là `"Soạn thư"` (`bounds: [615,1560][1008,1728]`). Kiểm tra chuỗi `"Soạn thư"` thô trong XML sẽ khiến script nhầm tưởng Inbox là màn hình Compose, liên tục gửi lệnh `keyevent 4 (Back)` -> app Gmail bị đóng và văng về màn hình trước đó, gây timeout `OTP_FETCH_TIMEOUT`.
- **Khắc phục**: Chỉ xác định màn hình Soạn thư khi có ID vùng soạn thảo `compose_area`, hoặc đồng thời có trường người nhận và tiêu đề (`"Đến"` và `"Chủ đề"`), hoặc `"Soạn email"`. Tuyệt đối cấm kiểm tra bare string `"Soạn thư"`.

---

## 3. Bẫy Nhầm Lẫn "Đồng bộ ngay" với Gmail DIE
- **Nhầm lẫn thường gặp**: Thấy app Gmail hiện thông báo *"Tài khoản chưa được đồng bộ hóa... Hãy nhấn Đồng bộ ngay"* thì tưởng rằng Gmail đã bị DIE / Checkpoint.
- **Thực tế**: Tài khoản hoàn toàn **LIVE 100%**. Đây là tính năng nhắc bật Master Auto-Sync mặc định của app Gmail trên máy farm khi chế độ đồng bộ nền của hệ thống đang tắt để tiết kiệm pin/data.
- **Khắc phục**: Khi gặp banner này, chỉ cần tap nút *"Đồng bộ ngay"* (`bounds [48,924][1032,1073]` -> toạ độ `540, 998`) hoặc vuốt xuống làm mới (`swipe 500 400 500 1400 300`) thì thư OTP sẽ đổ về Inbox ngay lập tức. Dấu hiệu Gmail DIE thật sự là thông báo *"Yêu cầu thực hiện hành động trên tài khoản"* (`Account action required`) hoặc popup checkpoint số điện thoại.

---

## 4. Bẫy Gộp Thư (Email Threading) & Trích Xuất Sai Mã OTP Cũ
- **Hiện tượng**: Khi yêu cầu gửi lại mã OTP nhiều lần, Gmail gom tất cả các email từ OpenAI vào chung 1 luồng trò chuyện (thread).
- **Hậu quả**: Nếu dùng `re.search(r'\b\d{6}\b', xml)` quét toàn bộ cây XML, regex sẽ bắt phải mã OTP của email cũ nằm ở phần trích dẫn trước đó (ví dụ bốc mã `667903` cũ thay vì `928955` mới). Khi gửi sai mã OTP quá 2-3 lần, OpenAI kích hoạt cơ chế rate-limit bảo vệ: `error_code: max_check_attempts` (*"Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại"*), làm treo tài khoản 15-30 phút.
- **Khắc phục**: Duyệt cây XML theo thứ tự `root.iter("node")` và chỉ trích xuất mã OTP từ **node đầu tiên** xuất hiện có chứa từ khóa `"tiếp tục:"` hoặc `"mã xác minh"`. Node đầu tiên trên danh sách/cây UI luôn là bản tóm tắt của thư mới nhất.

---

## 5. Cấm Mở Lại URL Đăng Ký (Signup URL) Khi Quay Lại Chrome
- **Hiện tượng**: Ở Step 3, khi chuyển từ Gmail quay lại Chrome, nếu thấy màn hình chưa ở domain OpenAI thì chạy `am start -a ... -d https://chatgpt.com/auth/login?screen_hint=signup`.
- **Hậu quả**: Lệnh `am start` với URL sẽ tải lại (reload) toàn bộ trang web, hủy bỏ form nhập OTP đang chờ sẵn và làm OpenAI báo: *"Phiên của bạn đã kết thúc. Tiếp tục bằng cách đăng nhập hoặc dùng ChatGPT.com mà không cần tài khoản"*.
- **Khắc phục**: Chỉ đưa Chrome lên foreground bằng `am start -n com.android.chrome/org.chromium.chrome.browser.ChromeTabbedActivity` hoặc `keyevent 4 (Back)` để quay lại tab đang chờ OTP. Tuyệt đối **CẤM** mở lại link signup khi đang ở giữa luồng chờ OTP.
