# Ưu tiên 2FA Authenticator trước OTP Email & Đồng bộ Hotmail Token qua GPM

## 1. Nguyên tắc Bất Di Bất Dịch: Ưu Tiên 2FA Authenticator Trước OTP Email
- **Bối cảnh phát hiện**:
  Khi tài khoản TikTok đã cài đặt 2FA Authenticator, màn hình checkpoint đăng nhập trên thiết bị đôi khi mặc định hiển thị luồng gửi mã xác minh về Email (`Sử dụng liên kết này hoặc nhập mã được gửi đến a***@gmail.com`).
- **Bẫy Classifier chết người**:
  - Tiêu đề màn hình hiển thị `"Xác minh 2 bước"`. Nếu matcher gom cả `"xac minh 2 buoc"` vào `TWOFA_HINTS`, script sẽ ngộ nhận đây là ô nhập TOTP Authenticator và điền mã 6 số TOTP vào ô Email OTP -> TikTok từ chối liên tiếp 3 lần dẫn tới STOPPED.
- **Quy trình giải quyết chuẩn**:
  1. Phân biệt rõ hai loại nhãn trên màn hình 2FA:
     - Nhãn Authenticator thuần túy: `"ung dung xac thuc"`, `"authenticator app"`, `"trinh xac thuc"`, `"google authenticator"`.
     - Nhãn Email OTP: `"gui den"`, `"email"`, `"nhap ma duoc gui den"`.
  2. **LUÔN ƯU TIÊN 2FA AUTHENTICATOR**:
     - Khi màn hình 2FA đang ở dạng Email OTP, kiểm tra xem có nút `"Sử dụng phương thức khác"` (`"Su dung phuong thuc khac"` / `"Use another method"` / tọa độ `[408, 1098]`) hay không.
     - Bấm `"Sử dụng phương thức khác"`.
     - Bấm chọn `"Trình xác thực"` / `"Ứng dụng xác thực"` (`Authenticator App`).
     - Lấy secret TOTP từ tracking (`taikhoan_dat_v2_updated .xlsx`) sinh mã và điền vào.
  3. **Chỉ fallback sang Email OTP** khi màn hình không có lựa chọn Authenticator hoặc tài khoản không có khóa secret trong database.

## 2. GPM Profile & Hotmail Graph API OTP Coordination
- **Yêu cầu an toàn GPM Profile**:
  - Mọi GPM Profile được tạo tự động qua `create_profile` / API v3 BẮT BUỘC gán proxy đúng theo mapping máy (`PROXYgandienthoai.xlsx`), đồng thời GPM tự động sinh ngẫu nhiên toàn bộ thông số fingerprint phần cứng, WebGL, Canvas, User-Agent.
- **Quy trình đọc Hotmail OTP**:
  - Với các tài khoản Hotmail đã có Refresh Token Graph API: Ưu tiên đọc OTP trực tiếp qua Graph API trên PC (`read_tiktok_otp_from_graph_token`), tuyệt đối không mở app Outlook trên thiết bị.
  - Với tài khoản Hotmail chưa có token Graph: Có thể đăng nhập password lên Profile GPM để giữ phiên web live, hỗ trợ kiểm tra hòm thư và đọc mã xác nhận.

## 3. Quản lý Kho Backup OneDrive
- **Quy tắc dồn kho**:
  - Gom toàn bộ các file backup tự động sinh ra (`.bak`, `.backup_before_*`, `tx_snap_*`) vào thư mục `workbook-backups/archive_history/`.
  - Giữ thư mục gốc OneDrive sạch sẽ, chỉ chứa các canonical workbook đang hoạt động (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik1.xlsx`-`Tik8.xlsx`, `PROXYgandienthoai.xlsx`, `master_gmail_manager.xlsx`).
