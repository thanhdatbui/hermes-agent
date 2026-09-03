# Magic-link flow — session máy 75 & máy 78 (2026-08-17)

Diễn tiến reg TikTok máy 75 (`ce011711d4cd802905`, `GayeGaebel4667@hotmail.com`) & máy 78 (`ce0916090a9d320a01`, `DebiDenbesten20198@hotmail.com`) khi TikTok
tự đổi OTP → magic-link hoặc luồng OTP 6 số. Toàn bộ bài học để tái lập/tránh lặp lỗi.

## Diễn tiến & Các lỗi mới phát hiện (Cập nhật 2026-08-17 đêm)

1. **Email form vs Popup Login:**
   - Màn hình "Tạo tài khoản" nhập email có liên kết "Chuyển sang dùng số điện thoại" -> classifier nếu kiểm tra marker `"so dien thoai"` trước sẽ bị nhầm sang `login_popup` và cố tìm nút "Tiếp tục với email" -> PENDING vô lý.
   - **Fix:** State `signup_email_form` (`dia chi email` + `chuyen sang dung so dien thoai`) phải được check TRƯỚC `login_popup`.

2. **False positive màn hình "Kiểm tra hộp thư của bạn":**
   - Danh sách `success_hints` của `wait_login_success` từng chứa `"Hộp thư"` / `"Hop thu"` -> match nhầm với tiêu đề *"Kiểm tra hộp thư của bạn"* -> script ngỡ đã đăng nhập thành công rồi tap nhầm nút "Gửi lại email" làm tab Profile -> STOPPED.
   - **Fix:** Xóa bỏ hoàn toàn `"Hộp thư"`, `"Hop thu"` khỏi `success_hints`.

3. **Cơ chế TikTok Magic-link Session Ticket (Root cause lỗi "Đã xảy ra lỗi. Hãy đảm bảo sử dụng cùng thiết bị"):**
   - Khi ở màn hình *"Kiểm tra hộp thư của bạn"*, TikTok lưu tạm một Ticket phiên trong RAM của `SignUpOrLoginActivity`.
   - Nếu `am force-stop` hoặc đóng task trong Recent apps trước khi kích hoạt deeplink, Ticket trong RAM bị hủy -> khi deeplink kích hoạt, TikTok mở phiên mới không khớp ticket -> báo lỗi thiết bị.
   - **Bắt buộc:** Phải giữ nguyên app TikTok chạy nền ở đúng màn hình *"Kiểm tra hộp thư của bạn"* trong suốt quá trình lấy và kích hoạt link xác minh!

4. **WebView trong Outlook nuốt XML node:**
   - Trong giao diện đọc email của Outlook, nút đỏ "Xác minh email" nằm trong WebView đôi khi không expose bất kỳ node con nào ra UiAutomator XML dump (`XML LEN` chỉ ~9KB).
   - **Fix:** `_atx_click_link_button` phải có fallback click trực tiếp vào tọa độ trung tâm nút đỏ `(540, 1460)` qua ATX JSON-RPC khi không parse được XML node.

5. **Date Picker Focus & Nút Tiếp tục (Máy 78):**
   - Nút "Tiếp tục" của Date Picker có bounds `[96, 1704][984, 1872]` -> tọa độ tap chuẩn là `(y1 + y2) // 2 = 1788` (trước bị bug `y1 + 24 = 1728` chạm trượt vào mép trên).
   - Ưu tiên click qua ATX JSON-RPC trước khi fallback `input tap`.

6. **Lỗi "Nhập đúng mã PIN" / OTP hết hạn (Máy 78):**
   - Khi mã OTP cũ không đúng hoặc hết hạn, màn hình DatePicker bị khóa không cho submit nút "Tiếp tục".
   - **Fix:** Tự động detect marker `nhap dung ma pin` / `invalid code` -> tap nút "Gửi lại mã" (`rid=ktj`) -> đọc mã OTP mới từ Graph API -> nhập mã mới để mở khóa.

7. **Workbook Lock (PermissionError [Errno 13]):**
   - Khi file `gmail_clean_v2.xlsx` bị mở bởi Microsoft Excel trên máy host, Graph token reader không đọc được token -> tưởng nhầm là không có token rồi fallback sang Outlook app. Phải đóng file Excel trước khi chạy.
