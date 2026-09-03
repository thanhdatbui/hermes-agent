# Quy tắc Vận hành Router Transparent Proxy & Cơ chế Phân loại Device Lock (30/08/2026)

## 1. Cơ chế Router Transparent Proxy (MikroTik + Sing-box + DHCP Aruba)
- **Bỏ hoàn toàn app ViChanger và interface `tun0`**: Các máy trên farm kết nối Wi-Fi thông thường (`wlan0`), router tự động định tuyến proxy theo IP cố định và có Kill Switch phần cứng.
- **Preflight Live Check Bounded**:
  - Gửi lệnh ping nhanh: `adb shell ping -c 1 -W 1 8.8.8.8` (timeout $\le 3s$).
  - Thu thập Egress IP công khai: `adb shell /data/local/tmp/atx-agent curl --timeout=3s http://icanhazip.com`.
  - Phân định route: Explicit `interface` ("wlan0" / "tun0") luôn có độ ưu tiên cao nhất, đè cấu hình `TAADAA_PROXY_MODE`.
- **Fail-Closed Không Treo**:
  - Đối với Router Mode (`wlan0`): Nếu mất mạng, chỉ thử bật lại Wi-Fi 1 lần (`svc wifi enable`), nếu vẫn fail thì throw `ConsumerPreflightError` ngay lập tức. **TUYỆT ĐỐI CẤM** gọi vòng lặp recovery ViChanger watcher hay soft-reboot làm nghẽn hàng đợi các máy khác.

---

## 2. Quy tắc Phân loại Device Lock & Thu hồi Dead-Owner (User Correction)

### Phân biệt 2 loại lỗi:
1. **Lỗi UI / App thật (Có Farm Alert + Banner Đỏ)**:
   - Hiện trường thực tế đang hiển thị lỗi trên màn hình điện thoại (Captcha, popup lạ, kẹt flow).
   - **Xử lý**: Giữ nguyên hiện trường (`status: blocked`) với TTL = **1 giờ** (60 phút) để operator vào debug.
2. **Lỗi Host / Crash Script / Preflight (Không có lỗi UI trên máy)**:
   - Điện thoại chưa mở app TikTok hoặc đang ở màn hình Home bình thường.
   - **Xử lý**: Khi tiến trình owner (PID) trên máy tính đã chết (`owner_alive == False`), **BẮT BUỘC nhả lock ngay lập tức**, không được giữ `blocked` làm tê liệt cả farm ở các đợt cron sau.

---

## 3. Tự động Up Avatar cho Video đầu tiên (Video #1)
- Khi tài khoản đăng **Video #1** lần đầu tiên (`video_number == 1` hoặc `Video Đã Đăng == 0`):
- Workflow `ENSURE_AVATAR` trong `D:\Taadaa\Tiktok-video` tự động kích hoạt đẩy `avatar.jpg`/`avatar.png` trong folder video tương ứng lên Profile TikTok mà không cần cấu hình `-ForceAvatarMachineList` thủ công.
