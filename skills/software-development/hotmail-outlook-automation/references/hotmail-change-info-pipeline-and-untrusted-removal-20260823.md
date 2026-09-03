# Hotmail Change-Info Full Pipeline & Recovery Email Untrusted Removal

## 1. Mục tiêu & Nguyên tắc bảo vệ Hotmail sau 7 ngày
- **Thời hạn 7 ngày (`MIN_LOGIN_AGE_DAYS = 7`)**: Hotmail login vào máy/farm đủ 7 ngày mới chạy change-info để tránh bị Microsoft checkpoint/khóa do thay đổi thông tin quá sớm.
- **Quy định BoxTaiKhoan**: Shop chỉ bảo hành 24h. Sau 7 ngày, người mua bắt buộc phải đổi thông tin để tránh bị lộ hoặc hack lại. Đổi password lập tức vô hiệu hóa OAuth2 `refresh_token` của shop.
- **Xử lý Mail Khôi Phục của Shop (Getnada, Fviainboxes...)**:
  - Không bắt buộc phải gán Gmail cá nhân (`thanhdatbui1995@gmail.com`) khi nuôi/xuất bán.
  - Quét trang `account.live.com/proofs/manage/additional` và gỡ bỏ trực tiếp các mail domain tạm của shop (`getnada`, `inboxes`, `fvia`, `tempmail`...).
  - Xóa trực tiếp trong Security và xác nhận modal thì có hiệu lực ngay lập tức, **tuyệt đối không chọn 'Tôi không còn quyền truy cập vào các thông tin này'** để không bị dính bẫy pending 30 ngày.

## 2. Chuỗi 4 bước thực hiện chuẩn trên máy Farm
1. **Tiền kiểm & Lock**:
   - Acquire Device Lock trên máy đích (`full_scope_takeover=True`).
   - Bật và verify VPN Proxy qua `D:\Taadaa\gan-proxy\scripts\gan_proxy_fleet.py`.
2. **Đổi Mật Khẩu (Change Password)**:
   - Mở `https://account.live.com/password/Change` qua Chrome trên máy Android.
   - Nhập mật khẩu hiện tại -> Nhập mật khẩu mới an toàn (`Taadaa2026M<Máy>`).
   - Bắt marker thành công từ Microsoft (`password_change_success_marker`).
3. **Gỡ Mail Lạ của Shop (Remove Untrusted Recovery Emails)**:
   - Mở `https://account.live.com/proofs/manage/additional`.
   - Tìm các email lạ của shop (`task_remove_untrusted_recovery_emails`), bấm `Xóa` / `Remove` -> Xác nhận modal.
4. **Đăng Xuất Mọi Nơi (Sign out everywhere) & Cập nhật Excel**:
   - Bấm `Đăng xuất khỏi mọi nơi` (`DeleteTrustedDevices`) -> Bắt marker `Chúng tôi đã bắt đầu đăng xuất cho bạn`.
   - Cập nhật `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`:
     - Cột C (`pass mail`): Cập nhật mật khẩu mới.
     - Cột E (`mail khôi phục`): Để trống nếu không gắn mail riêng.
     - Cột I (`token`): Clear trống.
     - Cột K (`ghi chú`): Đánh dấu `SECURED_YYYYMMDD` để script sau này tự động bỏ qua.
   - Nhả Device Lock an toàn.

## 3. Lưu ý Mapping Serial & Môi trường
- **Taikhoan Run Safe Mapping (`taikhoan_run_safe.xlsx`)**: Đảm bảo cột `Device ID` (Col 2) của tất cả các dòng của từng máy khớp đúng 1 Device Serial duy nhất. Tránh việc ghi nhầm ngày tháng vào cột serial làm fail preflight `MACHINE_SERIAL_MISMATCH`.
- **Environment Var**: `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/kibe.yaml"` bắt buộc có trong môi trường để preflight resolve đúng mapping path.
