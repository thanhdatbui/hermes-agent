# TikTok Login 2FA Email OTP: Cấm bỏ dở & Flow xử lý trọn gói (2026-09-17)

## 1. Rủi ro chí mạng khi bỏ dở màn hình 2FA Email OTP
- **Cơ chế chuyển đổi xác thực của TikTok**: Khi runner hoặc người dùng nhập mật khẩu thành công và màn hình chuyển sang `Xác minh 2 bước` (gửi OTP về Email Hotmail/Outlook), **TUYỆT ĐỐI KHÔNG ĐƯỢC BỎ DỞ / KHÔNG ĐƯỢC DỪNG LẠI HỎI USER KHI CHƯA NHẬP MÃ**.
- **Bẫy Magic Link & Rate Limit**:
  - Nếu gửi yêu cầu OTP nhưng không điền mã vào ô xác minh trong vài lần liên tiếp, TikTok sẽ kích hoạt cờ chống brute-force/bot và tự động chuyển đổi phương thức xác minh sang **Magic Link qua Email** hoặc khoá tạm thời với rate limit 900 giây (`wait 900s`).
  - Khi đã chuyển sang Magic Link, luồng tự động điền mã 6 số sẽ bị vô hiệu hóa hoàn toàn, buộc phải mở link xác thực trên trình duyệt thiết bị, làm tăng độ phức tạp và nguy cơ checkpoint tài khoản.

## 2. Quy trình xử lý E2E bắt buộc khi chạm màn hình 2FA Email
1. **Không dừng flow**: Khi app yêu cầu mã OTP gửi về `i***k@hotmail.com`, runner phải tự động thực thi ngay nhánh đọc hòm thư thay vì dừng lại hỏi xin phép.
2. **Khai thác hộp thư Hotmail/Outlook**:
   - Nếu có OAuth token (`refresh_token` / `client_id`): Dùng Microsoft Graph API qua `hotmail_provider.read_tiktok_otp_from_graph_token(...)` để lấy mã ngay lập tức (độ trễ < 3s).
   - Nếu không có OAuth token (nick cũ trong DAT): Mở app Outlook trên thiết bị (`com.microsoft.office.outlook`), đăng nhập bằng email & password từ Master DAT (`taikhoan_dat_v2_updated .xlsx`), hoàn tất onboarding và vào `Hộp thư đến`.
3. **Đọc mã & Xử lý hết hạn**:
   - Quét email mới nhất từ TikTok (`... là mã gồm 6 chữ số của bạn`).
   - Nếu mã cũ quá thời hạn (>5 phút hoặc báo `Mã xác minh email đã hết hạn`), bấm nút `Gửi lại mã` (`id/lch`), kéo reload inbox Outlook (swipe từ y=500 xuống y=1200), lấy mã mới nhất.
4. **Điền mã & Submit hoàn tất**:
   - Quay lại TikTok, xóa mã cũ bằng phím DEL (`keyevent 67` x 8), gõ mã OTP 6 số mới qua ADB.
   - Bấm `Tiếp tục` (`id/pyz`), xác nhận mật khẩu hoặc ấn `Enter` (`keyevent 66`) để hoàn tất chuyển cảnh vào trang Profile.
   - Verify profile bằng node username/handle (`@username`), đảm bảo nick hiển thị đầy đủ thông số trước khi đưa máy về background (`keyevent 3`) và tắt màn hình (`keyevent 26`).

## 3. Khôi phục One-Tap Fast Login ("Chào mừng bạn trở lại")
- Khi bấm nút *"Thêm tài khoản"* ở đáy danh sách Switcher, TikTok thường mở màn hình **Fast Login ("Chào mừng bạn trở lại")** chứa cache các tài khoản từng đăng nhập trên máy đó.
- Ưu tiên tap trực tiếp vào dòng tài khoản trong danh sách Fast Login để khôi phục session ngay tại chỗ:
  - Nếu nick có 2FA TOTP: Nhập TOTP $\rightarrow$ Đăng nhập tức thì.
  - Nếu nick lưu session hoàn chỉnh: TikTok khôi phục thẳng vào Profile mà không cần challenge lại mật khẩu.

## 4. Cơ chế giải phóng Slot cho máy chạm trần 8 nick (Parasite Account Eviction)
- Khi máy chạm trần 8 nick mà thiếu nick chính (Row 1):
  - **BƯỚC 1: ĐỐI SOÁT TÌM NICK MỒ CÔI (PARASITE ACCOUNT)**:
    - So sánh 8 nick thực tế trên Switcher với 8 nick được phân bổ trong `taikhoan_run_safe.xlsx`.
    - Nick nào có trên máy thật nhưng **KHÔNG CÓ trong `taikhoan_run_safe.xlsx`** (do các đợt reg bù / swap trước đây chưa logout) chính là nick mồ côi.
  - **BƯỚC 2: SAO LƯU TRƯỚC KHI ĐĂNG XUẤT**:
    - Truy vết trong các bản backup của `taikhoan_dat_v2_updated .xlsx` để lấy đầy đủ: Tài khoản, Mật khẩu TikTok, Email đăng ký, Mật khẩu Mail.
    - Lưu trữ hồ sơ để chuyển sang máy còn slot trống (ví dụ máy chỉ có 6 hoặc 7 nick).
  - **BƯỚC 3: ĐĂNG XUẤT ĐƠN LẺ AN TOÀN TRÊN THIẾT BỊ**:
    - Chuyển sang nick mồ côi đó trên Switcher.
    - Vào `Hồ sơ` $\rightarrow$ `Menu 3 gạch (Menu hồ sơ)` $\rightarrow$ `Cài đặt và quyền riêng tư` $\rightarrow$ Cuộn xuống đáy $\rightarrow$ Chọn `Đăng xuất` đơn lẻ đúng tài khoản đó.
    - Sau khi đăng xuất, nút *"Thêm tài khoản"* xuất hiện trở lại ở đáy Switcher, sẵn sàng nạp nick chính.
