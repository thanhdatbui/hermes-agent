# Proxy Live Check & Empty Password Rules in TikTok Registration

## 1. Proxy Live Gate (VPN Preflight)
- **Chuẩn hóa theo automation-core:** Trước khi mở TikTok để đăng ký hoặc đăng nhập, BẮT BUỘC gọi `require_android_vpn(AdbClient(serial=...), required=True, verify_live_ip=True)` (hoặc `require_vichanger_connected` như repo `tiktok-luot nuoi acc`).
- **Cơ chế kiểm tra:**
  1. Kiểm tra interface `tun0` trạng thái `UP`.
  2. Kiểm tra `dumpsys connectivity` có Network connected qua VPN.
  3. **Live IP Verification:** Broadcast tới app ViChanger: `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` (thử lại tối đa 3 lần).
  4. Nếu không lấy được IP thật (app trả về lỗi, chuỗi rỗng hoặc timeout) -> **Fail-closed chặn ngay lập tức (`VPN_PREFLIGHT_BLOCKED`)**, tuyệt đối không mở TikTok/trình duyệt để tránh lộ IP gốc.

## 2. Empty Password Rule (Pass rỗng khi không hỏi pass)
- Flow đăng ký TikTok qua email/OTP/magic-link:
  - Nếu đi qua màn đặt mật khẩu: sinh pass ngẫu nhiên (10-16 ký tự, gồm Hoa + Thường + Số + Ký tự đặc biệt) -> nhập và lưu `password`.
  - Nếu flow KHÔNG có màn đặt mật khẩu (chỉ nhập mã OTP rồi vào thẳng trang chủ/profile): gán `tiktok_pw = ""` (để trống).
  - Tuyệt đối KHÔNG lưu mật khẩu tự chế/ảo khi tài khoản chưa thực sự được đặt pass trên app.
