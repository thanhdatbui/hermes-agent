# Chrome WebView Form Automation & Input Timing Pitfalls on Android (Samsung S7)

## 1. WebView XML Attribute Mapping & Node Matcher Blindspots
- **HTML placeholder vs. Android XML**: Trong Chrome WebView, `placeholder="Email address"` được chuyển thành thuộc tính `hint="Email address"`, trong khi `text=""` và `content-desc=""` vẫn rỗng.
- **HTML id/name vs. Android resource-id**: Thuộc tính `id="email"` hoặc `name="email"` được map sang `resource-id="email"`.
- **Pitfall**: Nếu helper `find_node_in_xml` chỉ duyệt `text`, `content-desc`, `resource-id`, việc tìm kiếm nhãn như `("Email address", "Địa chỉ email")` sẽ trả về `None` vì không so khớp với `hint`.
- **Khắc phục**:
  - Luôn thêm keyword kỹ thuật vào target: ví dụ `("Email address", "Địa chỉ email", "email")` để ăn theo `resource-id="email"`.
  - Hoặc mở rộng `node_has_target` để duyệt thêm thuộc tính `hint` từ UI XML node.

## 2. Input Focus Latency trên thiết bị cấu hình thấp (Samsung S7)
- **Độ trễ render bàn phím & focus**: Trên Samsung S7 / Android 8, sau khi `tap` vào ô input trong Chrome, WebView cần ít nhất 1.0s – 1.5s để dựng focus box và con trỏ nhấp nháy.
- **Pitfall**: Dùng `wait=0.5s` rồi gọi ngay `adb shell input text <string>` sẽ khiến ký tự bị drop hoàn toàn vào khoảng không (ô input vẫn trống).
- **Phím Back (`keyevent 4`)**: Tránh lạm dụng `input keyevent 4` ngay sau khi gõ chữ vì có thể làm mất focus, kích hoạt cơ chế blur/reset của web form hoặc giật màn hình.

## 3. Co dãn Viewport & Cơ chế ẩn bàn phím / Submit an toàn (Keyboard Distortion & Dismissal)
- Khi bàn phím ảo xuất hiện trên màn hình 1080x1920, viewport của Chrome bị nén từ `[0, 240][1080, 1920]` xuống `[0, 240][1080, 903]`.
- Nút submit (ví dụ: "Tiếp tục" / "Continue") bị đẩy từ tọa độ `[108, 1497][972, 1632]` lên `[108, 765][972, 900]`.
- **Pitfall**: Fallback tap theo tọa độ cứng (ví dụ `tap(540, 1500)` hoặc `tap(540, 1504)`) sẽ bấm trúng bàn phím ảo thay vì nút bấm. Đặc biệt tọa độ `(540, 1504)` rơi đúng vào phím **'g'** ở hàng giữa bàn phím ảo Samsung, khiến chuỗi text vừa nhập bị chèn thêm ký tự 'g' vào đuôi (ví dụ: `email@gmail.comg`), làm form báo lỗi "Email không hợp lệ" hoặc submit sai.
- **Quy tắc ẩn bàn phím an toàn (CẤM dùng `keyevent 4` VÀ CẤM dùng `keyevent 111`)**:
  - `keyevent 4` (KEYCODE_BACK) cực kỳ nguy hiểm trong Chrome/WebView: dễ kích hoạt Back navigation của trình duyệt, đóng form, hoặc quay lại trang trước làm mất session đăng ký.
  - `keyevent 111` (KEYCODE_ESCAPE) cũng CẤM DÙNG: Trên Samsung S7 / stock TouchWiz, khi Chrome đang active, `keyevent 111` sẽ kích hoạt shortcut thu nhỏ Chrome về launcher/background, làm đứt toàn bộ flow tự động.
  - **Phương án chuẩn**: Sau khi nhập email hoặc mật khẩu, gửi trực tiếp `keyevent 66` (KEYCODE_ENTER) để submit form trong WebView (trigger hành động tương đương tap "Tiếp tục" / "Continue" trên bàn phím ảo). Nếu cần ẩn bàn phím mà không submit, chỉ tap vào vùng header an toàn (title bar/vùng trống phía trên viewport, ví dụ `shell(device_id, "input", "tap", "540", "200")`).
- **Kỹ thuật gõ text và submit trong automation script**:
  - Dùng trực tiếp `shell(device_id, "input", "text", text)` kèm `shell(device_id, "input", "keyevent", "66")` (Enter) để submit ngay lập tức.
  - Sau khi gửi Enter, chờ `time.sleep(1.0)` đến `2.0s` để trang settle và cập nhật cờ `email_submitted = True`.

## 4. Reset Flag khi gặp Validation Error (Chống treo timeout)
- **Pitfall**: Sau khi bấm submit, gán ngay `email_submitted = True`. Nếu WebView báo lỗi validation (ví dụ: "Cần nhập email." do text bị drop), các vòng lặp tiếp theo bỏ qua bước gõ/submit và chuyển sang chờ OTP cho đến khi hết timeout (120s – 240s).
- **Khắc phục**:
  - Kiểm tra dấu hiệu validation error trong XML (`"Cần nhập email"`, `"Vui lòng nhập"`, `"is required"`).
  - Nếu phát hiện, reset ngay `email_submitted = False` và `email_typed = False` để tự động re-focus, gõ lại và submit lại ngay lập tức.

## 5. Clear Field chuyên dụng trong Chrome WebView (`clear_webview_field`)
- **Pitfall của `clear_field` chuẩn native / Ctrl+A**:
  - `clear_field` thông thường dùng `keyevent 29 --meta 113` (Ctrl+A) hoặc double/triple tap để bôi đen text.
  - Trong Chrome WebView, Ctrl+A hoặc thao tác drag/long-press rất dễ bị Chrome bắt nhầm vào URL bar (Omnibox), hoặc kích hoạt context menu Copy/Paste làm che khuất input và văng focus khỏi form web.
- **Giải pháp `clear_webview_field` (xóa 2 chiều an toàn bằng cursor keyevents)**:
  - Định vị focus: `tap(device_id, *coord, wait=0.3)`.
  - Di chuyển về cuối chuỗi & xóa lùi: `keyevent 123` (MOVE_END) + gửi 40 lần `keyevent 67` (DEL / Backspace).
  - Di chuyển về đầu chuỗi & xóa tiến: `keyevent 122` (MOVE_HOME) + gửi 40 lần `keyevent 112` (FORWARD_DEL).
  - Quét dọn dự phòng: gửi thêm 20 lần `keyevent 67`.
  - Cơ chế này thuần keyevent con trỏ, không chạm vào clipboard/selection context menu, không giật trúng thanh địa chỉ URL của Chrome.

## 6. Phân Biệt Nút Nổi (FAB) "Soạn thư" vs Màn Hình Soạn Thảo Gmail
- **Pitfall**: Kiểm tra `if "Soạn thư" in xml: press Back` để thoát bản nháp nếu vô tình tap nhầm. Trên Inbox mặc định của Gmail luôn có nút nổi tròn (FAB) mang text `"Soạn thư"` (`bounds: [615,1560][1008,1728]`). Kiểm tra bare text `"Soạn thư"` khiến script ngộ nhận Inbox là Compose và liên tục ấn Back làm văng app Gmail.
- **Khắc phục**: Chỉ nhận diện màn hình Compose khi thấy ID `compose_area`, hoặc đồng thời có `"Đến"` và `"Chủ đề"`, hoặc `"Soạn email"`.

## 7. Banner "Đồng bộ ngay" KHÔNG PHẢI Gmail DIE
- **Bản chất**: Khi tạo tài khoản mới trên máy farm có Master Auto-Sync tắt, Gmail hiện: *"Tài khoản chưa được đồng bộ hóa... Nhấn Đồng bộ ngay"*. Đây là thông báo nhắc tính năng, tài khoản hoàn toàn **LIVE 100%**.
- **Khắc phục**: Tap *"Đồng bộ ngay"* (`bounds [48,924][1032,1073]` -> `540, 998`) hoặc vuốt xuống làm mới (`swipe 500 400 500 1400 300`) thì thư sẽ về ngay. Dấu hiệu DIE thật sự là thông báo *"Yêu cầu thực hiện hành động trên tài khoản"* (`Account action required`).

## 8. Bẫy Luồng Thư Gộp (Thread) & Lỗi OpenAI Rate-Limit `max_check_attempts`
- **Pitfall**: Khi gửi lại mã OTP nhiều lần, Gmail gộp tất cả thư OpenAI vào 1 thread hội thoại. Quét regex toàn bộ XML sẽ vô tình lấy trúng mã OTP của email cũ nằm ở phần trích dẫn phía dưới thay vì email mới nhất trên đỉnh. Nhập sai OTP 2-3 lần khiến OpenAI khóa tạm thời: `error_code: max_check_attempts` (15-30 phút).
- **Khắc phục**: Duyệt cây UI XML theo thứ tự `root.iter("node")` và chỉ lấy mã xác minh từ **node đầu tiên** có chứa `"tiếp tục:"` hoặc `"mã xác minh"`. Node đầu tiên luôn chứa preview của thư mới nhất.

## 9. Cấm Reload URL Đăng Ký Khi Chuyển Tab Về Chrome
- **Pitfall**: Ở Step 3, khi chuyển từ Gmail quay lại Chrome, nếu thấy màn hình chưa ở domain OpenAI thì gọi `am start -a ... -d https://chatgpt.com/auth/login?screen_hint=signup`. Tải lại URL sẽ hủy form nhập OTP đang mở sẵn và làm OpenAI báo: *"Phiên của bạn đã kết thúc"*.
- **Khắc phục**: Chỉ đưa Chrome lên foreground bằng `am start -n com.android.chrome/org.chromium.chrome.browser.ChromeTabbedActivity` hoặc `keyevent 4 (Back)` để quay lại đúng tab đang chờ mã.

## 10. Bẫy Màn Hình Tìm Kiếm Gmail (Search Mode Trap)
- **Pitfall**: Khi mở app Gmail (`com.google.android.gm`) để lấy mã OTP, ứng dụng có thể đang dừng ở chế độ tìm kiếm (`SearchView`) từ phiên trước hoặc do touch nhầm vào thanh tìm kiếm. Ở chế độ này, danh sách thư mới không được hiển thị và swipe refresh không cập nhật Inbox, dẫn đến timeout tìm OTP (90s).
- **Nhận diện trong XML**: Thấy thuộc tính text/content-desc `"Quay lại"` kèm theo các dấu hiệu tìm kiếm: `"Tìm kiếm trong thư"`, `"Bắt đầu tìm kiếm bằng giọng nói"`, hoặc filter chips như `"Tệp đính kèm"`.
- **Khắc phục**: Kiểm tra và tap nút Quay lại (Back icon) ở góc trên bên trái thanh search để thoát về Inbox:
  ```python
  if "Quay lại" in xml and any(k in xml for k in ["Tìm kiếm trong thư", "Bắt đầu tìm kiếm bằng giọng nói", "Tệp đính kèm"]):
      logger.info(f"[{device_id}] Gmail đang ở màn hình tìm kiếm, tap Quay lại để về Inbox...")
      tap(device_id, 72, 168, wait=1.5)
      xml = get_ui_xml(device_id) or ""
  ```

