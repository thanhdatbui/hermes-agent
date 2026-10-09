# ChatGPT Direct Email OTP & Automation Canary Gate Enforcement

Ngày đúc kết: 19/09/2026.
Bối cảnh: Liên kết ChatGPT qua Direct Email OTP (CẤM Google SSO) trên Samsung Galaxy S7 (Android 8.0) sau khi reg Gmail, tích hợp kỷ luật Canary Gate và Anti-Confabulation Protocol.

---

## 1. Kỷ Luật Canary Gate & Định Nghĩa Hoàn Thành (Done Gate)

### Quy tắc tối cao:
- **Phạm vi áp dụng:** CHỈ BẮT BUỘC khi sửa code **AUTOMATION** (các repo điều khiển thiết bị Android/phone farm: `register gmail`, `tiktok-*`, `automation-core`). Các tác vụ tài liệu, công cụ thuần, backend web, cấu hình, data sync: tự động bypass.
- **Thực thi bằng máy qua Exit Code (`D:/Taadaa/tools/done_gate.py`):**
  + Task general ➔ `exit 0` (Bypass).
  + Task automation + có bằng chứng Canary máy thật (< 2h) ➔ `exit 0` (PASS).
  + Task automation + chưa có Canary + farm có máy rảnh ➔ **`exit 1` (HARD BLOCK)**. CẤM Agent declare DONE hay dừng giữa chừng ở Unit test mock / Git commit.
  + Task automation + chưa có Canary + farm bận 100% ➔ `exit 0` (Deferred, ghi cờ `.canary_pending`).

### Anti-Confabulation Protocol (Cấm lấp liếm & bào chữa):
- CẤM TUYỆT ĐỐI phản xạ bao biện, rewrite lịch sử ("em tưởng", "thừa 1 nhịp hỏi", "khắc cốt ghi tâm", "lần sau sẽ chú ý").
- Khi bị phát hiện sai sót hoặc thiếu sót, format phản hồi DUY NHẤT được chấp nhận:
  ```text
  [FAULT-CONFIRMED]: <Tên lỗi cụ thể>
  - Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
  - Root Cause: <Nguyên nhân kỹ thuật thực tế>
  - Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
  - Verification: <Lệnh chạy kiểm chứng thực tế>
  ```

---

## 2. Các Cạm Bẫy Kỹ Thuật Khi Tự Động Hóa Chrome WebView & Gmail Trên S7

### Cạm bẫy 1: Bẫy Tap Omnibox Chrome `(540, 200)`
- **Hiện tượng:** Sau khi gõ email/OTP, code tap `(540, 200)` để ẩn bàn phím ảo. Thay vì ẩn phím, Chrome lập tức nhảy sang trang tìm kiếm Google Search với danh sách gợi ý và bàn phím tiếp tục mở.
- **Root Cause:** Trên màn hình Samsung S7 (1080x1920), dải Y = 60..220 chính là **thanh địa chỉ Omnibox** của Google Chrome. Tap vào đây sẽ kích hoạt focus URL bar và hủy focus khỏi trang web ChatGPT.
- **Giải pháp:**
  + TUYỆT ĐỐI KHÔNG tap Y < 300 trên Chrome để ẩn phím.
  + Tọa độ tap an toàn để dismiss phím trên ChatGPT web là vùng trống phía trên form: `(540, 600..800)`.
  + Hoặc submit trực tiếp: nếu nút "Tiếp tục" đã render trong UI XML (thường ở Y ~ 760 khi bàn phím nổi), tap thẳng nút Tiếp tục mà không cần ẩn phím.

### Cạm bẫy 2: UI XML Bỏ Sót Attribute `hint` trong Chrome WebView
- **Hiện tượng:** Trang ChatGPT đã tải xong ô nhập email nhưng `find_node_in_xml(xml, "Email address", "Địa chỉ email")` luôn trả về `None`, dẫn đến script bị kẹt hoặc rơi vào fallback sai.
- **Root Cause:** Trên Chrome WebView của Android, thẻ HTML `<input type="email" placeholder="Email address">` được render thành node:
  ```xml
  <node text="" content-desc="" resource-id="email" hint="Email address" ... />
  ```
  Hàm kiểm tra `node_has_target` thông thường chỉ quét `text`, `content-desc`, `resource-id` mà bỏ qua `hint`.
- **Giải pháp:**
  + Trong `node_has_target` (của `gmail_reg_v10.py` hoặc các parser XML), BẮT BUỘC đưa `attrs.get("hint", "")` vào danh sách `values` đối chiếu.
  + Bổ sung target `"email"` khi tìm kiếm ô nhập email: `find_node_in_xml(xml, "Email address", "Địa chỉ email", "email", prefer_clickable=True)`.

### Cạm bẫy 3: App Gmail Kẹt Ở Tài Khoản Cũ / Trạng Thái "Đang nhận thư"
- **Hiện tượng:** Mở app Gmail bằng `am start com.google.android.gm/.ConversationListActivityGmail` để lấy OTP OpenAI, nhưng màn hình chỉ hiện thông báo *"Đang nhận thư của bạn..."* hoặc không thấy email OpenAI.
- **Root Cause:**
  + Nếu trên máy S7 đang có tài khoản Google khác bị lỗi xác thực (`authentication-error`), Android Sync Manager bị treo `internal-error` trên `gmail-ls`.
  + App Gmail mặc định mở lại hòm thư của tài khoản trước đó, không tự động chuyển sang tài khoản mới vừa tạo.
- **Giải pháp:**
  + Kiểm tra header xem Gmail đang ở tài khoản nào.
  + Nếu chưa đúng tài khoản mục tiêu: tap vào header container tài khoản `com.google.android.gm:id/og_bento_account_management_header_container` tại tọa độ `(540, 380)` để mở danh sách tài khoản, sau đó tap chọn đúng email mục tiêu.
  + Với tài khoản mới tạo, tăng số vòng lặp chờ đồng bộ lên tối thiểu 25 vòng (~55s) kèm thao tác vuốt nhẹ để refresh hòm thư (`swipe 500 400 500 1200 300`).

### Cạm bẫy 4: Xung Đột Persistent Context Khóa File Khi Chạy Song Song
- **Hiện tượng:** Nhiều tiến trình worker chạy song song gọi `check_gmail_is_live()` đồng thời bị crash hàng loạt với lỗi: `BrowserType.launch_persistent_context: Target page, context or browser has been closed`.
- **Root Cause:** Tất cả tiến trình dùng chung một đường dẫn cố định `USER_DATA = r"D:/Taadaa/GPM auto/checkmail_proxy_data"`. Chrome Chromium không cho phép 2 tiến trình mở chung 1 profile cùng lúc.
- **Giải pháp:** Tách thư mục profile động theo PID và nano-timestamp:
  ```python
  unique_user_data = f"{USER_DATA}_{os.getpid()}_{time.time_ns()}"
  ```
  Và bắt buộc đặt lệnh dọn dẹp thư mục tạm trong khối `finally:` sau khi `context.close()`.
