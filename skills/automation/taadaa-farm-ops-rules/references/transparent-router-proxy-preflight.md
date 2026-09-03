# Transparent Router Proxy (Wi-Fi + Gateway Ping) & Auto Avatar Rules

Use this reference when operating, testing, or updating network preflight, device proxy routing, and upload flows across all farm repositories (`automation-core`, `tiktok-luot nuoi acc`, `tiktok-follow`, `Tiktok-video`).

## 1. Migration from App VPN (ViChanger) to Router Transparent Proxy
- **Bối cảnh:** Toàn bộ dàn máy Android (160 máy) được định tuyến Proxy cố định tại tầng Router (MikroTik + Sing-box + DHCP Aruba). Điện thoại kết nối trực tiếp qua Wi-Fi (`wlan0`, dải IP `192.168.10.x`), có Kill Switch phần cứng tại router (nếu proxy die thì router ngắt mạng).
- **Loại bỏ ViChanger & tun0:**
  - Thiết bị không còn interface `tun0` và không chạy package `vn.vichanger.app`.
  - Vô hiệu hóa và không chạy watcher gán proxy trên Windows (`GanProxyWatcherTray` / `proxy-watcher-only-tray.ps1`).
  - Gửi lệnh `am force-stop vn.vichanger.app` để giải phóng hoàn toàn các tunnel VPN treo ngầm.

## 2. Preflight Network Verification Protocol
1. **Dual-Route Routing:**
   - Khi `interface == "wlan0"` hoặc `TAADAA_PROXY_MODE == "router"`: Kiểm tra `wlan0` UP + `dumpsys connectivity` có `WIFI CONNECTED`.
   - Khi `interface == "tun0"` (legacy): Chỉ kiểm tra `tun0` và dumpsys VPN, không tự ý probe `wlan0`.
2. **Gateway Ping & Android Validation Probe (< 0.3s):**
   - Sing-box / Transparent Proxy định tuyến TCP/UDP (HTTP/HTTPS/DNS) nhưng thường DROP gói tin ICMP raw ping tới internet (`8.8.8.8`).
   - Do đó, bước probe internet tầng router kiểm tra:
     a. Ping Gateway Router (`192.168.10.254` hoặc `192.168.10.1`) để xác nhận link Wi-Fi vật lý.
     b. Kiểm tra cờ `VALIDATED` / `INTERNET` trong `dumpsys connectivity` (được NetworkMonitor của Android tự động xác thực).
   - Nếu cả 2 đều mất kết nối -> Fail-closed ngay lập tức để bảo vệ nick và không gây nghẽn hàng đợi.
3. **Triệt tiêu vòng lặp Recovery trên Router Mode:**
   - Thiết bị chạy `wlan0` khi mất mạng: Chỉ thử `svc wifi enable` 1 lần (sleep 2s). Nếu vẫn không thông -> Báo lỗi `ConsumerPreflightError` ngay lập tức.
   - **Tuyệt đối cấm gọi ViChanger recovery watcher hoặc soft-reboot trên thiết bị Router Proxy.**

## 3. Video #1 Auto Avatar Upload (`ENSURE_AVATAR`)
- **Quy tắc:** Khi nick đăng video lần đầu tiên (`Video Đã Đăng == 0` -> đăng **Video #1** / `video_number == 1`):
  - Workflow `ENSURE_AVATAR` trong `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py` tự động kích hoạt bước up Avatar từ file `avatar.jpg`/`avatar.png` trong folder video tương ứng.
  - Không cần cấu hình `-ForceAvatarMachineList` thủ công.
  - Các lần đăng video sau (Video #2, #3, ...) sẽ giữ nguyên avatar hiện tại trừ khi có cờ ép buộc rõ ràng.

## 4. Farm Alert & Device Lock Separation
- **Lỗi UI Thật (Có Farm Alert & Banner Đỏ):** Khi script gặp lỗi UI TikTok (kẹt popup, profile lỗi, upload fail, follow fail), hệ thống chụp ảnh Banner Đỏ gửi Telegram và đánh dấu `blocked`, **giữ hiện trường 90 phút (TTL 5400s)** để operator debug màn hình.
- **Lỗi Host / Script Crash (Không có hiện trường UI):** Nếu lỗi xảy ra ở tầng preflight/host code trước khi thao tác UI hoặc PID chết bất đắc dĩ, **BẮT BUỘC nhả lock ngay lập tức** (cấm ngâm lock mù làm tê liệt farm).
- **Phạm vi Farm Alert:** Giám sát toàn bộ ca nuôi acc bao gồm Feed session, Follow hook (`tiktok-follow`) và Upload hook (`tiktok-video`).
