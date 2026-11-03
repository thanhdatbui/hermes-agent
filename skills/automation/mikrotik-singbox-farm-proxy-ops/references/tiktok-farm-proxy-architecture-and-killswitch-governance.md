# TikTok Farm Proxy Architecture: Sing-box Container vs. L3/L4 Hardware Kill-Switch & Anti-Leak Governance

## 1. Bản Chất Hiện Tượng Rò Rỉ IP Gốc (Leak IP) Trên Android (S7)
- **Vấn đề lịch sử (ViChanger / HTTP Proxy thông thường):**
  - Cài proxy trực tiếp trên Android qua Wi-Fi settings hoặc ViChanger chỉ bắt luồng **TCP**. Chrome chạy TCP nên khi proxy chết sẽ ngắt mạng.
  - **TikTok App chạy engine riêng (`Cronet / TTNet`):** Mặc định ưu tiên truyền video và API qua **QUIC / HTTP/3 (UDP port 443)** và truy vấn DNS trực tiếp (**UDP port 53**).
  - Khi proxy TCP chết hoặc timeout, TikTok app kích hoạt cơ chế **Fail-Open**: lén bỏ qua proxy và bắn thẳng các gói tin UDP 443 / DNS 53 ra gateway để tải video. Nếu router không chặn cứng ở tầng firewall, **toàn bộ video và API của nick sẽ chạy bằng IP gốc (leak IP)** dẫn đến việc bị ByteDance đánh gậy/bóp reach.

## 2. Vì Sao Sing-box Container L7 Làm CPU MikroTik x86 Chạm Trần 95%
- **Hiện tượng 105.000 PPS (Packets Per Second) với băng thông chỉ 120 Mbps:**
  - Kích thước gói tin trung bình $\approx 143$ bytes/packet (bão gói tin ACK Storm và UDP fragmentation).
  - **Context-Switching & Dual-VETH Loop:** Gói tin từ Phone đi vào bridge $\to$ veth-singbox $\to$ Sing-box user-space (epoll, unpack, rewrite) $\to$ veth-singbox lần 2 $\to$ WAN. Một gói tin video bị băm nhỏ và xử lý ngắt phần mềm (`softirq`) tới 2 lần trên cùng 1 CPU bus.
  - **Cạm bẫy Sing-box Log Level:** Đặt `log.level = "info"` trên 160 listeners khiến container ghi hàng chục nghìn dòng log/giây qua veth vào bộ nhớ $\to$ BẮT BUỘC đặt `log.level = "warn"`.
  - **Sing-box 1.12+ Migration Trap:** Bắt buộc có `"default_domain_resolver": "dns-direct"` trong block `route` nếu không container sẽ crash exit code 1 (`ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER`).

## 3. Kiến Trúc Tối Ưu: L3/L4 Quad-Lock Kill-Switch Trên MikroTik (Bỏ Container L7, Giảm CPU < 15%)
Để điện thoại trỏ proxy trực tiếp sang Thái Bình (MobiProxy/R3G) mà **an toàn 100% không bao giờ leak IP**, MikroTik RouterOS triển khai **Bộ Tứ Phòng Thủ (Quad-Lock)** ở tốc độ dây (wire-speed):

1. **Khóa IPv6 toàn diện:** Vô hiệu hóa IPv6 trên interface farm (`/ipv6 settings set disable-ipv6=yes`), triệt tiêu cơ chế *Happy Eyeballs* của TikTok.
2. **Loại trừ FastTrack 2 chiều:** Cấm FastTrack cho dải IP farm (`src-address=!192.168.110.0/24` và `dst-address=!192.168.110.0/24`) để chống việc connection bypass filter rules.
3. **Chặn UDP lén:** Drop hoặc Reject UDP 443 (QUIC) và UDP 53 (DNS) từ dải farm.
4. **Strict Forward Default-Deny:**
   - Rule 1: Cho phép S7 kết nối nội bộ tới PC Kibe (`.123`) và PC Admin (`.119`) để giữ kết nối ADB.
   - Rule 2: Cho phép `src-address-list=FARM_S7_DEVICES` kết nối ra ngoài DUY NHẤT tới `dst-address-list=THAI_BINH_PROXIES` (ports `5101–5158`).
   - Rule 3: `chain=forward src-address-list=FARM_S7_DEVICES action=drop` (DROP TOÀN BỘ traffic còn lại ra WAN).
   - *Kết quả:* Proxy Thái Bình chết $\to$ S7 bị ngắt mạng hoàn toàn, không lọt dù chỉ 1 byte ra IP gốc.

## 4. Tẩy Uế & Bảo Mật Tinyproxy (R3G Thái Bình): Elite Anonymous
- Mặc định Tinyproxy chèn header `Via: 1.1 r3g-tp5141 (tinyproxy)` làm lộ dấu vết proxy trung gian với ByteDance.
- **Cách xóa dấu vết:** Trong `/etc/tinyproxy/instances/tp_*.conf` và `generate_all_proxies.sh`:
  - Bỏ dòng `ViaProxyName`.
  - Thêm dòng: `DisableViaHeader Yes`.
  - Reload daemon: `killall -HUP tinyproxy`.
  - Xác thực qua `httpbin.org/headers`: không còn header `Via` hay `X-Forwarded-For`.

## 5. Kỷ Luật Đồng Bộ Scan Guard (Chống Tự Khóa):
- Khi WAN IP MikroTik Đà Nẵng đổi: BẮT BUỘC script tự động hóa (`update_mikrotik_scan_guard.py`) phải đồng thời cập nhật:
  1. Box MobiProxy qua API `proxy.scan_guard.save`.
  2. Router R3G qua SSH Tailscale (`100.115.94.49`) cập nhật dòng `Allow <MikroTik_WAN_IP>` vào 16 file config Tinyproxy và `killall -HUP tinyproxy`.
  - Tuyệt đối CẤM chỉ chạy script thủ công 1 lần rồi báo xong mà bỏ quên cronjob định kỳ 5 phút.
