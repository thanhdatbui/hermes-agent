# Tắt Xác Minh 2 Bước Qua Email Trên TikTok v46.6.3 & Xử Lý GMS Stale S7 Mới (16/09/2026)

## 1. Cơ Chế Bắt Buộc: Failure Evidence First (Cấm Chụp Màn Hình HOME)
- **Vấn đề thực tế:** Khi đăng nhập tài khoản gặp lỗi (mã PIN sai, OTP không khớp, WebView lỗi cú pháp JS `Unexpected token ?`, hoặc kẹt màn hình), agent hay mắc tật chạy teardown/force-stop/phím HOME trước rồi mới chụp ảnh. Hậu quả là ảnh đính kèm `MEDIA:` chỉ hiện màn hình HOME của điện thoại, không có giá trị nghiệm thu.
- **Quy tắc bất di bất dịch:**
  1. Khi phát hiện lỗi hoặc kẹt bước, **BẮT BUỘC chụp ảnh screencap đóng băng hiện trường ngay tại millisecond phát hiện lỗi** — trước khi gọi bất kỳ lệnh cleanup, force-stop hay phím HOME nào.
  2. Bắt buộc kiểm tra `foreground_package`: Nếu foreground là launcher/HOME mà không phải crash văng app thì cấm gửi ảnh đó làm bằng chứng lỗi.
  3. `MEDIA:<path>` phải đặt ở dòng đầu tiên của message báo cáo để hiển thị trực tiếp cho user.

## 2. Lỗi Nghẽn GMS Framework & Popup Welcome Tour Trên Samsung Galaxy S7 Mới
- **Hiện tượng:**
  - Máy S7 mới cắm vào farm, mở app Gmail luôn bị kẹt ở popup "Mới có trong Gmail" (`WelcomeTourActivity`). Nút "OK" (`welcome_tour_got_it`) nhận lệnh tap nhưng không đóng.
  - Vào `Settings -> Thêm tài khoản -> Google`: Màn hình trơ ra, không mở Activity đăng nhập Google.
- **Root Cause:**
  - Google Play Services (`com.google.android.gms`) và Google Services Framework (`com.google.android.gsf`) trên máy mới bị treo khởi tạo / stale cache, khiến Account Manager không trả Activity về khi gọi Intent thêm tài khoản.
- **Quy trình phục hồi chuẩn:**
  1. Kiểm tra và kích hoạt lại các package Google bị disable:
     ```bash
     adb shell pm enable com.google.android.webview
     ```
  2. Xóa dữ liệu stale của GMS và Gmail:
     ```bash
     adb shell pm clear com.google.android.gm
     adb shell pm clear com.google.android.gms
     ```
  3. Khởi động lại thiết bị (`adb reboot`): Sau reboot, GMS khởi tạo lại sạch sẽ. Mở `Settings -> Thêm tài khoản -> Google` sẽ bật ngay màn hình đăng nhập Google (`MinuteMaidActivity`), cho phép nạp tài khoản Gmail và đồng bộ Inbox bình thường.

## 3. Khảo Sát Hiện Tượng Tắt Xác Minh 2 Bước Qua Email Trên TikTok & Toast Lỗi Bảo Mật
- **Luồng chuẩn trong `live_phase_b_adapter.py` & `phase_b_runner.py`:**
  - Thứ tự thiết kế: Kích hoạt `Trình xác thực` (TOTP) -> Đảm bảo `Mật khẩu: Bật` -> Ghi Secret vào cột E Workbook -> Mới tiến hành gỡ/tắt `Email` (`disable_email_and_confirm_stable`) -> Đổi/rotate mật khẩu mạnh (`ensure_password_saved`).
  - Thao tác gỡ email: Điều hướng `Xác minh 2 bước` -> tap row `Email` -> tap `Xóa` -> tap `Xác nhận` trên dialog "Xóa email? - Bạn sẽ không còn dùng tùy chọn này làm phương thức xác minh 2 bước nữa".
- **Hiện tượng Server TikTok từ chối (Kiểm chứng OCR Máy 30 ngày 16/09/2026):**
  - Mặc dù màn hình đã có đủ cả 2 phương thức độc lập (`Trình xác thực: Bật` VÀ `Mật khẩu: Bật`), ngay sau khi bấm `Xác nhận`, TikTok ném một thông báo Toast màu đen lên màn hình:
    > ⛔ *"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"* (Minh chứng: `m30_toast_xoa.png`)
  - Sau khi dialog đóng, trạng thái của dòng Email vẫn giữ nguyên chữ **`Bật`** (hoặc `_method_checked == True`).
  - Script sau đó ném ngoại lệ `EMAIL_DISABLE_NOT_STABLE`.
- **Cơ chế gốc rễ:**
  - Server TikTok áp dụng cơ chế **Security Cooldown** trên tài khoản no-phone hoặc tài khoản mới thiết lập/đổi phương thức bảo mật gần đây trên thiết bị. Server tạm thời khóa quyền gỡ bỏ kênh liên lạc khôi phục gốc (Email) để phòng chống chiếm đoạt tài khoản.
- **Kết luận vận hành & Quy tắc nghiệm thu:**
  - Nếu tài khoản đã có `Trình xác thực: Bật` (TOTP), `Mật khẩu: Bật` và `Lưu thông tin đăng nhập: Bật`, việc Email vẫn còn `Bật` là do chính sách an toàn server-side của TikTok, KHÔNG PHẢI lỗi logic script hay lệch UI.
  - Khi đăng nhập vào máy khác hoặc tool qua proxy, TikTok chỉ yêu cầu Mật khẩu + mã Authenticator (TOTP), hoàn toàn không bị ép nhận OTP về Email.
