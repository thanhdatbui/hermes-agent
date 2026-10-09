# TikTok 46.x Account Switcher One-Tap Fast Login & 2FA Recovery (2026-09-17)

## Bối cảnh & Hiện tượng
1. Trên farm TikTok v46.x (Samsung S7 Android 7/8), khi runner báo `manual-needed:account-switcher-missing-expected` hoặc không thấy nick Row 1 trên danh sách Switcher:
   - Thường xuyên do: (a) App hiển thị Display Name thay vì `@username`; hoặc (b) Nick bị văng khỏi Switcher hiển thị nhưng VẪN CÒN NẰM TRONG CACHE THIẾT BỊ.
2. Tại màn hình "Thêm tài khoản", TikTok thường hiển thị danh sách One-Tap Login ("Chào mừng bạn trở lại, <username>") của các tài khoản đã từng đăng nhập trước đó trên máy.
3. Khi click vào tài khoản One-Tap, TikTok sẽ yêu cầu Xác minh 2 bước (2FA):
   - Phương thức 1: Mã gửi về ứng dụng xác thực (TOTP).
   - Phương thức 2: Mã gửi về Email (Hotmail/Outlook).

## Pitfall chí mạng: Hỏi thay vì tự động nhập mã OTP khi đã mở màn hình 2FA
- **Triệu chứng & Hậu quả**: Khi mở màn hình 2FA (dù là TOTP hay Email OTP), mã OTP có thời hạn (thường là 60s đếm ngược, hoặc liên kết hết hạn trong vài phút). Nếu agent dừng lại hỏi user thay vì lấy mã nhập ngay, yêu cầu đăng nhập sẽ bị bỏ dở hoặc quá hạn.
- **Bẫy Magic Link**: Nếu runner hoặc agent kích hoạt bước nhập mật khẩu / yêu cầu gửi mã OTP nhiều lần nhưng không hoàn tất nhập mã xác minh, TikTok sẽ tự động chuyển cơ chế bảo mật sang bắt buộc xác minh qua Magic Link email hoặc khóa tạm thời (rate limit 900s), làm mất khả năng tự động đăng nhập.
- **Quy tắc bắt buộc**: Khi đã bấm vào tài khoản và màn hình 2FA hiện ra:
  1. Nếu là `Ứng dụng xác thực`: Ngay lập tức dùng secret TOTP trong Master DAT (`automation_core.totp.generate_totp(secret)`) gõ mã vào ô EditText và submit `Tiếp tục`.
  2. Nếu là `Email`: Ngay lập tức mở ứng dụng Outlook trên máy (hoặc API Microsoft Graph) đọc thư mới nhất của TikTok, trích xuất mã 6 số, quay lại TikTok điền mã và submit. TUYỆT ĐỐI KHÔNG dừng lại hỏi user giữa chừng khi mã đang chờ nhập.

## Quy trình khôi phục tài khoản Row 1 bằng One-Tap Fast Login
1. **Kiểm tra slot trống trên máy thật (Zero-Risk Audit)**:
   - Mở Switcher trên máy thật, đếm số lượng tài khoản thực tế.
   - Nếu có < 8 tài khoản (ví dụ 6 hoặc 7 tài khoản) $\rightarrow$ VẪN CÒN NÚT "Thêm tài khoản", TUYỆT ĐỐI KHÔNG logout bất kỳ tài khoản nào khác.
2. **Kích hoạt One-Tap Fast Login**:
   - Tap nút `Thêm tài khoản` ở đáy Switcher.
   - Kiểm tra màn hình "Chào mừng bạn trở lại": Nếu thấy nick mục tiêu, tap trực tiếp vào dòng của nick đó.
   - Nếu màn hình rơi vào form Đăng ký (`Tạo tài khoản` / `Đăng ký TikTok`):
     - Gửi phím BACK hoặc tìm nút `Bạn đã có tài khoản? Đăng nhập` ở đáy màn hình.
     - Sau khi bấm `Đăng nhập`, màn hình One-Tap Cache sẽ xuất hiện lại.
3. **Vượt qua 2FA tức thì**:
   - Nếu màn hình là `Ứng dụng xác thực`:
     - Tap ô nhập mã `bounds=[90,660][990,816]`.
     - Sinh mã TOTP: `code = generate_totp(secret)`.
     - `adb shell input text <code>` $\rightarrow$ Tap `Tiếp tục`.
   - Nếu màn hình là `Email`:
     - Kiểm tra hòm thư Outlook trên máy thật (`com.microsoft.office.outlook`).
     - Đọc mã OTP 6 số từ thư mới nhất của TikTok.
     - Nếu mã hết hạn: Bấm `Gửi lại mã` $\rightarrow$ Chuyển sang Outlook vuốt làm mới để lấy mã OTP mới $\rightarrow$ Nhập vào TikTok.
4. **Xác nhận hoàn tất**:
   - Sau khi login, app tự chuyển về Home Feed hoặc trang Profile.
   - Tap tab Hồ sơ $\rightarrow$ Vuốt nhẹ đưa Profile về đỉnh $\rightarrow$ Dump XML xác nhận `id/t4g` (Display Name) hoặc `id/t6l` / `id/sxa` (`@username`).
   - Gửi `input keyevent 3` (HOME) và `input keyevent 26` (Tắt màn hình) để đưa thiết bị về trạng thái nghỉ an toàn.
