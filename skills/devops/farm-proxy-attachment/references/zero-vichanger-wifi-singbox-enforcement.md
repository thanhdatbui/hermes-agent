# Zero ViChanger Policy & Wi-Fi Singbox / MikroTik Enforcement (2026-10-17)

## Bối Cảnh Lịch Sử & Sự Cố (2026-10-17)
- **Hiện tượng:** Runner upload / workflow bị soft-reboot, sau reboot văng thông báo: `proxy watcher did not publish post-reboot readiness` hoặc `proxy readiness timed out`.
- **Cạm bẫy:** Agent ngộ nhận là hệ thống thiếu service ViChanger watcher (`GanProxyWatcherTray` / `gan_proxy_fleet.py watch`) và cố gắng bật lại hoặc tìm VPN `tun0` trên điện thoại.
- **Sự thật kiến trúc farm:**
  * Farm đã **BỎ HOÀN TOÀN VICHANGER** từ tháng 9/2026.
  * Toàn bộ 80 máy Kibe chạy proxy tĩnh qua **tầng Wi-Fi (Aruba AP) kết hợp Container Singbox trên router MikroTik** (`192.168.110.2:20001..20080`), gán qua `global http_proxy`.
  * Dàn Admin (201..280) chạy qua cổng LAN MikroTik PPPoE `192.168.110.2:10008..10035`.
  * Điện thoại **KHÔNG CÓ VPN `tun0`**, không mở app ViChanger, và không dùng watcher cấp lại IP sau reboot.

## Quy Tắc Vận Hành Bất Biến
1. **CẤM BẬT VICHANGER:** Tuyệt đối không bật task `GanProxyWatcherTray`, không chạy `gan_proxy_fleet.py watch`, không gửi broadcast `START_VPN` lên bất kỳ máy nào trong farm.
2. **Xử lý Timeout Readiness Sau Reboot:**
   * Lỗi `proxy readiness timed out` sau soft-reboot là do file cờ cũ trong `C:\Users\Kibe\.codex\device-readiness/<serial_hash>.json` kẹt trạng thái chờ watcher.
   * Để giải phóng: Xóa file marker hoặc gọi:
     ```python
     from automation_core.readiness import mark_proxy_state
     mark_proxy_state('<serial>', 'proxy_ready')
     ```
   * Không cố tìm hay bật lại app ViChanger trên điện thoại.
