# Singbox Proxy Stalling on MikroTik PPPoE Outage (2026-10-09)

## Hiện tượng
Preflight của runner trên thiết bị Kibe (ví dụ Máy 16) báo lỗi:
```
[PREFLIGHT_VPN_BLOCKED] required Android VPN is not connected: 
interface=wlan0 tun_up=False vpn_connected=True error=global proxy (192.168.110.2:20016) egress IP verification failed: 
Get "http://ifconfig.me/ip": context deadline exceeded
```

## Chẩn đoán phân tầng
1. **Upstream MobiProxy (`test.taadaa.click:51xx`):**
   - Probe trực tiếp từ host qua `urllib.request` hoặc `curl -x` có authentication (`mobiX:TaadaaMobi#2026!`).
   - Nếu trả về public IPv4 và latency <150ms $\to$ Box MobiProxy và upstream 4G hoạt động bình thường.
2. **Cụm Singbox Container (`veth-singbox` trên `192.168.110.2`):**
   - Đọc log MikroTik (`/log`):
     `container,info,debug ... ERROR ... lookup test.taadaa.click: context deadline exceeded`
   - Đọc trạng thái PPPoE trên MikroTik (`/interface/pppoe-client`):
     `PPPoE Clients: 0/60 running` (các interface `pppoe-out1..pppoe-out60` đều `disconnected`).
3. **Bản chất kỹ thuật:**
   - Singbox (`172.17.0.2`) cấu hình phân giải DNS qua UDP tới `8.8.8.8`.
   - Khi toàn bộ 60 đường PPPoE FPT trên router MikroTik bị ngắt kết nối (hoặc ISP bảo trì), routing table `main` của MikroTik không có default route ra Internet.
   - Do đó, container Singbox không thể gửi truy vấn DNS ra ngoài, làm mọi kết nối tới `test.taadaa.click` bị ngắt tại bước phân giải tên miền (`lookup test.taadaa.click: context deadline exceeded`).
   - Cổng proxy local `192.168.110.2:200xx` vẫn mở TCP socket trong LAN nhưng mọi request đi qua đều bị timeout.

## Quy tắc xử lý
- **Không suy diễn sai:** Không nhầm lẫn giữa lỗi MobiProxy 4G và lỗi đường truyền PPPoE FPT của MikroTik.
- **Fail-closed đúng thiết kế:** Preflight chặn lại là hoàn toàn chính xác để chống direct IP leak.
- **Giữ nguyên hàng đợi PENDING:** Giữ trạng thái `PENDING` trong SQLite (`avatar_replace_queue`), không đánh dấu FAIL hay DONE. Watchdog sẽ tự động đẩy khi đường truyền PPPoE hồi phục.
