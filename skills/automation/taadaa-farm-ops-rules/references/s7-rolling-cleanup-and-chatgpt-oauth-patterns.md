# S7 Rolling Cleanup & In-Device ChatGPT OAuth Registration Patterns

Ngày đúc kết: 15/09/2026.
Bối cảnh: Tự động hóa đăng ký tài khoản ChatGPT liên kết Google OAuth trực tiếp trên điện thoại Samsung Galaxy S7 (Android 8.0 / API 26) sau khi reg Gmail thành công, kết hợp cơ chế Preflight Check Live và gỡ bỏ cuốn chiếu tài khoản Google DIE khỏi hệ điều hành Android.

---

## 1. Cơ chế Hook ChatGPT Google OAuth On-Device (Chống False-Positive)

### Mục đích:
- Thay thế warmup newsletter (Cooperpress, Ruby Weekly, v.v. - thực tế các trang này đều bật Cloudflare Turnstile, request POST ảo không bao giờ gửi thư về).
- Đăng ký ChatGPT bằng Google OAuth ngay trên điện thoại S7 để nhận thư xác nhận bảo mật chính thức từ Google và OpenAI về app Gmail nhằm tăng trust, xóa bỏ rủi ro tài khoản bị quét Ghost Account.
- Tận dụng IP MobiProxy 4G vừa reg Gmail để thực hiện OAuth.

### Các cạm bẫy & Giải pháp:
1. **Lỗi báo cáo ảo (False-Positive Trap):**
   - Vòng lặp chờ tìm nút nếu timeout mà không `return False` ngay sẽ trôi xuống cuối hàm, script tự chụp ảnh màn hình và báo `success: True`.
   - **Kỷ luật:** Mọi bước (Cookie, Dialog Chrome, Password, Consent, About-you) bắt buộc phải xác minh bằng UI XML thực tế (`step_verified = True`). Nếu hết deadline mà chưa qua bước, BẮT BUỘC chụp ảnh lỗi hiện trường và return `{"success": False, "status": "FAILED_AT_<STEP>", ...}` ngay lập tức.
2. **Dialog hệ thống "Đăng nhập vào Chrome":**
   - Trên Android 8.0, khi bấm *"Tiếp tục với Google"* trong Chrome, hệ thống thường bật popup: *"Đăng nhập vào Chrome - Đăng nhập vào trang web này và Chrome để sử dụng dấu trang..."*.
   - **Giải pháp:** Quét text `"Đăng nhập vào Chrome"` hoặc `"sử dụng dấu trang"` -> tap ngay nút `"Bỏ qua"` / `"Skip"` (tọa độ fallback `(540, 1800)`).
3. **Nhập mật khẩu trên WebView S7:**
   - Khi Google yêu cầu nhập mật khẩu (`challenge/pwd`), thẻ tiêu đề vẫn hiển thị email mục tiêu. Nếu `find_node_in_xml` email đặt trước, script sẽ tap nhầm vào tiêu đề lặp lại đến timeout.
   - **Giải pháp:** Ưu tiên kiểm tra màn hình `challenge/pwd` trước màn hình chọn tài khoản (`Account Chooser`).
   - Ký tự đặc biệt (đặc biệt là dấu `!`) bị ADB shell escape sai -> bắt buộc dùng helper `human_type`.
   - Sau khi gõ mật khẩu, submit bằng `shell(device_id, "input", "keyevent", "66")` (phím Enter ảo) đạt độ tin cậy cao nhất trên WebView S7.
4. **Trang About-You (auth.openai.com/about-you):**
   - Màn hình hỏi *"Bạn bao nhiêu tuổi? - OpenAI"*: tự động tính tuổi từ DOB (hoặc mặc định 26), gõ tuổi, ẩn bàn phím (`keyevent 4`) rồi tap nút Tiếp tục `(540, 1698)`.
5. **Cổng nghiệm thu cuối cùng (Success Gate):**
   - Đặt deadline chờ 30s để WebView tải xong `chatgpt.com` trên mạng 4G.
   - Chỉ xác nhận thành công khi xuất hiện các chỉ số ChatGPT (Welcome, Message ChatGPT, URL `chatgpt.com` không còn auth).

---

## 2. Preflight Check Live & Gỡ tài khoản Google DIE khỏi Android Settings

### Bối cảnh:
- Mỗi máy Samsung S7 trên farm chứa tối đa 5-8 tài khoản Google.
- Trước khi chạy reg Gmail mới, cần giải phóng slot và dọn sạch các tài khoản đã bị Google checkpoint/vô hiệu hóa (DIE).
- Thao tác gỡ tài khoản phải thực hiện an toàn trên OS Cài đặt Android, CẤM đăng nhập web myaccount.

### Quy trình chuẩn:
1. **Preflight Check Live Real-time:**
   - Trích xuất danh sách tài khoản hiện có qua `dumpsys account`.
   - Gửi batch sang `checkmail.live` qua Playwright headless.
   - **Ưu tiên gỡ DIE ngay lập tức:** Nếu phát hiện bất kỳ tài khoản nào có trạng thái `DIE`, đánh dấu gỡ ngay mà không cần chờ điều kiện $\ge 5$ tài khoản hay thời gian ngâm 30 ngày.
2. **Lưu vết danh sách DIE:**
   - Khi gỡ thành công một tài khoản DIE, ghi ngay vào file tập trung: `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt` theo định dạng:
     `<email_die>|<machine_id>|<serial>|<YYYY-MM-DD HH:MM:SS>`
3. **Thao tác UI Android Settings trên Samsung Galaxy S7 (Android 8.0):**
   - **Mở giao diện:** `am start -a android.settings.SYNC_SETTINGS`.
   - **Bẫy điều hướng kẹt tài khoản cũ:** Nếu màn hình đang dừng ở chi tiết một tài khoản cũ (có nút *"XÓA TÀI KHOẢN"* hoặc *"Đồng bộ tài khoản"*), bắt buộc phải tap nút Trở về ở thanh header `(72, 144)` trước để đưa màn hình về danh sách tài khoản đầy đủ.
   - **Tránh lỗi uiautomator dump tty:** Lệnh `exec-out uiautomator dump /dev/tty` thường xuyên trả về rỗng trên Android 8.0 S7. Phải dùng cơ chế dump file an toàn:
     `uiautomator dump /sdcard/settings_dump.xml` sau đó `cat /sdcard/settings_dump.xml`.
   - **Các bước gỡ:**
     1. Tap vào mục `Google` (nếu giao diện gom nhóm).
     2. Tìm email mục tiêu trong XML -> Tap vào tọa độ email.
     3. Nhấn nút menu 3 chấm ở góc trên bên phải `(1000, 150)` hoặc nút *"XÓA TÀI KHOẢN"* trực tiếp.
     4. Chọn *"Xóa tài khoản"* trong menu popup.
     5. Xác nhận tại popup: tap *"Xóa tài khoản"* `(782, 1145)`.
     6. Verify lại qua `dumpsys account` để đảm bảo email đã biến mất khỏi hệ điều hành.
