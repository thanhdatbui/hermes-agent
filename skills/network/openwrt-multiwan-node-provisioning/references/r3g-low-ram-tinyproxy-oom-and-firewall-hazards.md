# Xiaomi R3G Low-RAM Tinyproxy OOM & OpenWrt Firewall Isolation Hazards

## 1. Bối Cảnh Sự Cố (Root Cause Incident 2026-10-31)
Trên router Xiaomi R3G (MediaTek MT7621A, 128MB RAM DDR3) chạy OpenWrt làm node multi-WAN từ xa qua Tailscale:
- **Hiện tượng:** Router sập kết nối Tailscale vĩnh viễn (`Online: False`), không phản hồi SSH port 22, cổng UDP 41641 và toàn bộ dải proxy `5141..5158`.
- **Nguyên nhân kép:**
  1. **OOM Killer do spawn quá nhiều tiến trình Tinyproxy:** Script cấu hình khởi chạy 8 tiến trình `tinyproxy` độc lập cho 8 interface PPPoE sub. Mỗi tiến trình cấu hình `MinSpareServers 2`, `MaxSpareServers 5`, dẫn tới tổng cộng 30–40 process Tinyproxy con chạy đồng thời. Với bộ nhớ hạn chế 128MB RAM, kernel Linux kích hoạt Out-Of-Memory (OOM) Killer tiêu diệt tiến trình nền ngốn bộ nhớ, trong đó có `tailscaled`.
  2. **Firewall reload cô lập interface Tailscale:** Lệnh `uci set firewall.allow_proxies=rule` với `src='tailscale'` và `/etc/init.d/firewall reload` khi chưa khai báo zone firewall fw3 đầy đủ cho device `tailscale0` đã khiến OpenWrt áp dụng chính sách mặc định (DROP) lên interface ảo `tailscale0`. Hậu quả: router tự cắt đứt kết nối Tailscale và drop toàn bộ traffic vào từ xa.

## 2. Các Quy Tắc Bất Biến (Invariants)
1. **Low-RAM Proxy Concurrency Cap:**
   - Trên router RAM <= 128MB (như Xiaomi R3G), TUYỆT ĐỐI CẤM chạy nhiều instance Tinyproxy độc lập.
   - Nếu cần proxy đa cổng đa line, BẮT BUỘC dùng **1 single process** (ví dụ Sing-box hoặc 3proxy cấu hình gộp 1 tiến trình lắng nghe nhiều cổng) với bộ đệm bộ nhớ tối thiểu.
2. **Kỷ Luật Can Thiệp Firewall Từ Xa Qua Tailscale:**
   - CẤM reload firewall (`/etc/init.d/firewall reload`) nếu chưa đảm bảo interface `tailscale0` nằm trong zone có `input ACCEPT`.
   - Mọi thao tác firewall trên node headless từ xa bắt buộc có cơ chế hẹn giờ rollback tự động (fail-safe timer):
     `sleep 60 && /etc/init.d/firewall restart &` trước khi test rule mới.
3. **Xung Đột Tailscale Service Start:**
   - CẤM gọi `tailscaled` thủ công trong `/etc/rc.local` khi đã kích hoạt service `/etc/init.d/tailscale enable` để tránh đụng port socket hoặc đụng socket file `/var/run/tailscale/tailscaled.sock`.
