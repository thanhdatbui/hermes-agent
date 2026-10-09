# TikTok Fast Login, 2FA Recovery & Chống Kẹt Chuyển Sang Magic Link (2026-09-17)

## 1. Cơ chế Nguy hiểm: Kẹt 2FA OTP chuyển sang Magic Link / Rate Limit 900s
- **Hiện tượng**: Khi bot hoặc người thao tác đăng nhập tài khoản TikTok, nếu đã qua bước nhập mật khẩu và TikTok nhảy vào màn hình **Xác minh 2 bước (2FA)** hoặc gửi mã OTP về email/ứng dụng xác thực:
  - NẾU dừng lại, bỏ dở màn hình OTP, hoặc thoát app mà không nhập mã, sau vài lần thử (hoặc vài phút bỏ trống) TikTok sẽ tự động **chặn hình thức xác minh bằng mã số** và chuyển sang bắt buộc xác thực bằng **Liên kết Magic Link** gửi về email, hoặc khóa thử lại với lỗi **"Bạn đã thử quá nhiều lần. Vui lòng thử lại sau" (Rate limit 900s)**.
  - Khi dính Magic Link: Việc tự động hóa đọc số OTP 6 chữ số qua API sẽ vô hiệu, buộc phải mở web/app để click link xác thực phức tạp, làm gián đoạn toàn bộ batch runner.
- **Quy tắc Vàng**: ĐÃ ĐẾN MÀN HÌNH OTP THÌ BẮT BUỘC PHẢI HOÀN TẤT LẤY OTP VÀ NHẬP VÀO NGAY LẬP TỨC. Tuyệt đối không dừng lại giữa chừng để hỏi user hay để màn hình chờ quá 60s!

## 2. Fast Login / Chào mừng bạn trở lại (One-Tap Account Recovery)
- Khi một nick cũ (ví dụ Row 1) bị mất khỏi Switcher visible (do máy chạm trần 8 nick hoặc danh sách bị ẩn), tài khoản đó thường **vẫn còn lưu phiên trong cache hệ thống**.
- Khi bấm nút **"Thêm tài khoản"** ở đáy Switcher, TikTok sẽ không đưa vào màn hình đăng ký mới mà đưa vào màn hình **"Chào mừng bạn trở lại"**:
  - Danh sách này liệt kê các tài khoản đã từng đăng nhập trên thiết bị (kèm nút "Đăng nhập" hoặc dòng tài khoản).
  - Bấm vào nick mục tiêu:
    - Trường hợp 1 (Phiên sống): TikTok khôi phục thẳng vào Profile không cần hỏi lại mật khẩu/2FA.
    - Trường hợp 2 (Cần 2FA): Nhảy vào màn hình Xác minh 2 bước (TOTP hoặc Email OTP).

## 3. Khôi phục 2FA qua TOTP Secret & Outlook App trên Samsung S7
- **2FA Ứng dụng xác thực (TOTP)**:
  - Nếu tài khoản có Secret trong Master DAT (`column 5` / `index 4` dạng Base32):
    Dùng hàm chuẩn `from automation_core.totp import generate_totp; code = generate_totp(secret)`.
    Nhập mã `code` vào `EditText` (`[90, 660][990, 816]`), sau đó bấm `Tiếp tục` (`[96, 1728][984, 1884]`).
- **2FA Email OTP (Hotmail/Outlook)**:
  - Nếu TikTok gửi mã 6 số về Hotmail:
    1. Kích hoạt ứng dụng Outlook trên máy: `adb shell monkey -p com.microsoft.office.outlook -c android.intent.category.LAUNCHER 1`.
    2. Đăng nhập Hotmail từ DAT nếu chưa đăng nhập (lưu ý: chọn "Thiết lập tài khoản Microsoft Outlook" thay vì IMAP để vào nhanh WebView OAuth).
    3. Vuốt xuống refresh hộp thư đến (`adb shell input swipe 540 500 540 1200 300`).
    4. Quét XML ATX trích xuất mã 6 chữ số từ tiêu đề thư TikTok (ví dụ: `861681 là mã gồm 6 chữ số của bạn`).
    5. Quay lại TikTok (`adb shell monkey -p com.ss.android.ugc.trill ...`) và nhập mã ngay trước khi hết hạn 60s.

## 4. Xử lý Trần 8 Nick & Nick Mồ Côi Ký Sinh (Parasite Accounts)
- Trước khi vội vàng logout nick mới reg (chưa có 2FA, dễ mất vĩnh viễn):
  1. Luôn đếm số nick thực tế trên Switcher: Nhiều trường hợp máy chỉ có 6–7 nick, vẫn còn nút "Thêm tài khoản" $\rightarrow$ Nạp thẳng không cần đá nick nào!
  2. Nếu máy đủ 8 nick kẹt cứng: So sánh 8 nick trên máy với danh sách `taikhoan_run_safe.xlsx`. Nick nào nằm trên máy thật nhưng KHÔNG CÓ trong Excel chạy an toàn chính là **Nick mồ côi / Nick ký sinh**.
  3. Kiểm tra file backup Excel (`taikhoan_dat_v2_updated .xlsx.bak...`): Các nick mồ côi này hầu hết đều có đầy đủ Pass + Hotmail từ các đợt chạy trước.
  4. Thực hiện logout đơn lẻ nick mồ côi từ `Cài đặt và quyền riêng tư` $\rightarrow$ `Đăng xuất` (chọn nick đích) để giải phóng 1 slot trống, sau đó nạp nick Row 1 vào.
