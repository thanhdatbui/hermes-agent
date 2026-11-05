# Đột Phá Kernel DNAT Toàn Farm, Xóa Bỏ Singbox, Dọn Sạch Cron Đổi IP Và Tối Ưu Conntrack (2026-11-05)

## 1. Bản Chất Sự Cố & Đột Phá Kiến Trúc (Zero L7 Proxy)
- **Vấn đề cốt tử ban đầu:** Con Mini PC MikroTik x86 RouterOS bị kẹt cứng ở mức 95% – 98% CPU do chạy Singbox Container L7 gánh hàng triệu gói tin video TikTok của 160 máy Samsung S7 (bão UDP/QUIC và context-switching qua card ảo `veth-singbox` lên tới 127.000 pps).
- **Thử nghiệm thất bại ban đầu:**
  1. Thử DNAT sang R3G bị timeout do lỗi Asymmetric Routing (16 đường PPPoE độc lập đẩy sai interface reply) và lỗi DNS ma của Tailscale (`100.100.100.100` trong `/etc/resolv.conf`).
  2. Bấm form hàng loạt trên web MobiProxy bị backend bỏ qua (silent drop), proxy vẫn bắt `auth strong`.
- **Giải pháp đột phá dứt điểm:**
  1. Dùng Playwright định vị chính xác ID `#access-save` trong thẻ HTML5 `<details>` và `<dialog>` của web MobiProxy, chuyển toàn bộ 38 cổng proxy đang chạy sang chế độ `none` (Không xác thực).
  2. Nạp 38 rule Kernel DNAT phần cứng trên MikroTik cho dàn Kibe (`20001..20038 ➔ 5101..5138`), đưa lên đứng trước rule Singbox `*30E`.
  3. Bổ sung script tự động hóa `sync_mikrotik_mobiproxy_dnat()` trong `update_mikrotik_scan_guard.py` và nâng tần suất cron lên 1 phút/lần (`* * * * *`) để tự động bắt dính IP WAN MobiProxy khi Viettel xoay IP.
  4. **KẾT QUẢ:** CPU con Mini PC MikroTik rơi thẳng đứng từ **97.6% xuống còn 0.4% – 1.6%**, độ trễ proxy giảm từ 1.5s xuống 0.45s wire-speed!

## 2. Dọn Sạch Cronjob Tự Đổi Proxy & Khóa Cố Định IP
- **Nguyên nhân farm Kibe thỉnh thoảng rớt mạng:** Cronjob `mobiproxy-auto-healer-watchdog` (`cron_mobiproxy_healer.py`) chạy ngầm mỗi 5 phút tự động kích hoạt API reset cổng MobiProxy khi thấy chập chờn, khiến IP bị đổi ngoài ý muốn của Operator.
- **Quy chuẩn dọn dẹp:** Đã xóa bỏ hoàn toàn vĩnh viễn cronjob `mobiproxy-auto-healer-watchdog` ra khỏi hệ thống (`cronjob(action='remove', job_id='7e5e3980dde1')`). CẤM tự ý tạo bất kỳ cron watchdog nào tự động kích hoạt reset cổng proxy nếu không có chỉ đạo trực tiếp của Operator.

## 3. Thu Hồi Bảo Mật VPS Hết Hạn & Dọn Rác Pipeline Lock
- **Thu hồi Peer WireGuard Doravo:** VPS Doravo đã hết hạn nhưng vẫn còn cấu hình Peer `*2` (`10.200.0.3/32`) trên interface `wg-remote` của MikroTik. Nguy cơ: Cloud provider tái cấp phát IP của VPS cho người khác có thể lợi dụng tunnel chui vào LAN farm. Đã xóa sạch Peer này trên MikroTik qua REST API.
- **Xử lý kẹt pipeline lock (`pipeline_repo_*.lock`):** Các phiên crash/reboot để lại file lock rác trong `D:/Taadaa/runtime/locks/`. Khi kiểm tra, nếu `psutil.pid_exists(pid) == False`, đó là stale lock và cần dọn dẹp để pipeline không bị chặn oan ở bước Precheck.

## 4. Bằng Chứng Thực Chứng (Ground Truth Telemetry)
- Kiểm tra trực tiếp trên điện thoại S7 Máy 1 qua 3 trang web quốc tế:
  * `icanhazip.com`: `117.5.179.223`
  * `httpbin.org/ip`: `"origin": "117.5.179.223"`
  * `whoer.net`: `117.5.179.223` (Anonymity 100%, Viettel Military Industry and Telecoms Group).
- Đo kiểm tải CPU MikroTik sau khi hoàn tất: `[0%, 1%, 1%, 0%, 0%]` -> Trung bình `0.4%`.
