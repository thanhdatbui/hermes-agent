# Kỷ Luật Tuyệt Đối Chống Hồi Sinh ViChanger & Bản Chất Proxy Wi-Fi Singbox

## 1. Sự cố ngộ nhận (2026-10-17)
- **Hiện tượng:** Khi runner upload TikTok trên Samsung S7 kích hoạt soft-reboot (do lỗi UI/popup), sau reboot script ném lỗi:
  `Guarded reboot recovery failed: proxy watcher did not publish post-reboot readiness after reboot` / `proxy readiness timed out for <serial>`.
- **Cạm bẫy tâm lý của Agent:** Thấy log có chữ "proxy watcher" và thấy Scheduled Task `GanProxyWatcherTray` trên Windows đang ở trạng thái `Disabled`, Agent tưởng nhầm là dịch vụ watcher bị thiếu và tự ý bật lại `GanProxyWatcherTray` hoặc chạy `gan_proxy_fleet.py watch`.
- **Hậu quả nghiêm trọng:** Người dùng lập tức tức giận vì Farm đã **BỎ HOÀN TOÀN VICHANGER** từ tháng 9/2026. Mọi hành vi bật lại watcher hay can thiệp vào app ViChanger trên máy điện thoại đều là vi phạm nghiêm trọng kỷ luật farm.

## 2. Bản chất kỹ thuật & Sự thật hạ tầng
1. **Toàn bộ 80 máy Kibe chạy qua tầng Wi-Fi Singbox trên MikroTik (`192.168.110.2:20001..20080`):**
   - Thiết bị được cấu hình `settings put global http_proxy 192.168.110.2:20000+N` và `captive_portal_mode 0`.
   - Mọi lưu lượng đi thẳng qua router MikroTik và container Sing-box.
   - **HOÀN TOÀN KHÔNG DÙNG APP VICHANGER**, không tạo VPN card `tun0` trên điện thoại.
2. **Tại sao lại có lỗi `proxy readiness timed out`?**
   - Đây là **tàn dư code cũ trong `state_machine.py` / `consumer repos`**: Sau khi reboot, script kiểm tra sự tồn tại của file marker trong `C:\Users\<User>\.codex\device-readiness\<hash>.json`.
   - Thời trước, file này do `GanProxyWatcherTray` ghi nhận sau khi gán VPN.
   - Nay farm chạy Wi-Fi Singbox tĩnh, proxy luôn sống sẵn qua router, nhưng đoạn code kiểm tra marker vẫn chạy và chờ một watcher vốn đã bị vô hiệu hóa.

## 3. Quy tắc ứng xử bắt buộc (Invariant)
1. **CẤM TUYỆT ĐỐI:**
   - CẤM bật lại Scheduled Task `GanProxyWatcherTray`.
   - CẤM chạy bất kỳ tiến trình nào của `gan_proxy_fleet.py` hay `proxy-watcher-only-tray.ps1`.
   - CẤM gửi lệnh `am broadcast` tới package `vn.vichanger.app` hoặc cố gắng mở app ViChanger.
2. **Cách xử lý chuẩn khi gặp `proxy readiness timed out`:**
   - **Giải phóng tức thì cờ readiness bằng Python (O(1)):**
     ```python
     import sys
     sys.path.insert(0, 'D:/Taadaa/automation-core/src')
     from automation_core.readiness import mark_proxy_state
     mark_proxy_state('<serial>', 'proxy_ready')
     ```
   - Lệnh này ghi trạng thái `proxy_ready` vào file JSON để runner tiếp tục bước tiếp theo ngay lập tức mà không cần bất kỳ tiến trình watcher nào.
3. **Ưu tiên fix gốc ở tầng UI:**
   - Nguyên nhân gốc khiến máy bị soft-reboot hầu hết là do popup UI TikTok (ví dụ: popup chúc mừng *"Tổng lượt thích"* che thanh header Profile).
   - Hãy fix dứt điểm việc nhận diện và bấm đóng popup ở UI (`adapter.py` / `state_machine.py`), máy sẽ không bị reboot và không bao giờ rơi vào nhánh chờ proxy readiness.
