# Router Transparent Proxy Preflight & Phân loại Device Lock (30/08/2026)

## 1. Cơ chế Router Transparent Proxy (Wi-Fi wlan0 + Ping + Egress IP)
- **Giao thức**: Chuyển toàn bộ farm 76-160 máy sang Wi-Fi `wlan0` qua Router MikroTik + Sing-box + DHCP Aruba, có Kill Switch phần cứng. Không còn app ViChanger và interface `tun0`.
- **Preflight Check chuẩn trong `automation-core` (`check_android_vpn`)**:
  1. Nhận diện route: `interface="wlan0"` / `interface="tun0"` (explicit) luôn thắng `TAADAA_PROXY_MODE`. Mặc định `auto`: probe `tun0` trước, nếu không có thì probe `wlan0`.
  2. Khi chạy Router mode (`wlan0`): Yêu cầu dumpsys `WIFI` CONNECTED + Ping `8.8.8.8` (timeout $\le 3s$) + trích xuất public egress IP qua `atx-agent curl http://icanhazip.com`.
  3. Khi preflight lỗi: Với router mode, chỉ thử `svc wifi enable` 1 lần rồi fail-closed ngay lập tức; **TUYỆT ĐỐI KHÔNG** gọi vòng lặp recovery ViChanger watcher / soft-reboot kéo dài gây nghẽn hàng đợi các máy khác.

---

## 2. Quy tắc Phân loại Device Lock: UI Error vs Host Crash (User Correction)

### Vấn đề gốc rễ:
Trước đây mọi exception (kể cả lỗi code Python / host crash khi điện thoại chưa hề mở app) đều set `status: blocked`. Script reaper giữ `blocked` 2 tiếng kể cả khi PID đã chết $\rightarrow$ Gây kẹt 66 máy và tê liệt các ca sau.

### Quy tắc chuẩn hóa:
1. **Lỗi UI / App thật (Có Farm Alert + Banner Đỏ)**:
   - Điện thoại đang hiển thị lỗi thật (Captcha, popup lạ, kẹt flow).
   - **Xử lý**: Giữ nguyên hiện trường (`status: blocked`) với TTL = **1 giờ** (giảm từ 2h xuống 1h) để operator vào debug.
2. **Lỗi Host / Python Crash / Preflight Failure (Điện thoại chưa chạy UI)**:
   - Điện thoại đang ở Home hoặc chưa mở TikTok.
   - **Xử lý**: Khi tiến trình owner (PID) trên máy tính đã chết (`owner_alive == False`), **BẮT BUỘC nhả lock ngay lập tức**, không được giữ `blocked` làm kẹt farm.

---

## 3. Tự động Up Avatar khi Đăng Video lần đầu (Video #1)
- Trong repo `D:\Taadaa\Tiktok-video` (`state_machine.py`), khi tài khoản đăng **Video #1** (`video_number == 1` / `Video Đã Đăng == 0`):
- Workflow `ENSURE_AVATAR` tự động kích hoạt đẩy `avatar.jpg`/`avatar.png` từ thư mục video nguồn lên Profile TikTok mà không cần cấu hình `-ForceAvatarMachineList` thủ công.
