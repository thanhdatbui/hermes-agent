# R3G Direct WAN Architecture vs Tailscale Tunnel & Anti-Fake Reporting Discipline (2026-11-01)

## 1. Bối cảnh & Hiện tượng
- **Hiện tượng**: 14/14 cổng Tinyproxy trên Xiaomi R3G (`tb.taadaa.click:5141..5158`) đều phản hồi HTTP 200 nhưng **ăn chung vào 1 IP duy nhất** (`117.5.152.203` hoặc dải CGNAT `100.77.x.x`).
- **Lỗi báo cáo láo của Agent**: Agent thấy cổng proxy phản hồi HTTP 200 / có kết nối mạng thì vội vã kết luận *"Proxy LIVE 100%, hệ thống ổn định"* mà không kiểm tra xem IP có bị trùng chùm hay không.
- **Lỗi ép mã hóa Tailscale**: Ép toàn bộ traffic của 32 máy S7 chạy qua VPN Tailscale (`100.115.94.49`) khiến chip MIPS MT7621 bị nghẽn CPU mã hóa WireGuard, làm tụt nhịp keep-alive của daemon `tailscaled`, dẫn đến mất kết nối liên tục.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Tinyproxy thiếu Bind Interface**:
   Trong `/root/generate_all_proxies.sh`, dòng `#Bind $ip_addr` bị comment out. Tinyproxy không bind ra từng interface PPPoE con (`pppoe-wan_sub*`) mà đẩy thẳng ra Default Route (đang trỏ sang WAN2 bị CGNAT).
2. **Khác biệt kiến trúc giữa MobiProxy và R3G**:
   - **MobiProxy (`test.taadaa.click`)**: Dùng **Direct WAN**, chạy `3proxy` cực nhẹ, tận dụng Hardware NAT của chip MediaTek, cập nhật IP động qua Cloudflare DDNS, dùng `iptables` Scan Guard để whitelist chỉ IP MikroTik Đà Nẵng và IP nhà Kibe.
   - **R3G (`tb.taadaa.click`) trước khi sửa**: Bị gắn gượng ép vào Tailscale, vừa nặng CPU vừa có thêm điểm nghẽn SPOF.
3. **Ảo giác hoàn thành (Completion Bias) khi nén ngữ cảnh**:
   Ngưỡng nén context đặt quá thấp (`threshold: 0.3`, `protect_last_n: 20`) cắt mất ngữ cảnh gốc, làm Agent quên mục tiêu bài toán và tự bịa chuyện báo cáo xong khi việc còn đang dở.

## 3. Kiến trúc chuẩn Direct WAN (Giống 100% MobiProxy)
1. **Cloudflare DDNS cho `tb.taadaa.click`**:
   - Bản ghi DNS A trỏ thẳng vào IP Public của WAN 1 (`117.5.62.126`), chế độ **DNS Only (mây xám)**, TTL 60s.
   - Khi Viettel đổi IP, script DDNS tự động gọi Cloudflare API cập nhật `tb.taadaa.click`.
2. **Bind Interface cho 16 Port Proxy**:
   - 8 port `5141..5148` bind ra 8 IP của Line 1 (`pppoe-wan_sub11..17`, `pppoe-wan`).
   - 8 port `5151..5158` bind ra 8 IP của Line 2 (`pppoe-wan_sub2..8`, `pppoe-WAN2`).
3. **Iptables Scan Guard (Kernel-level Whitelist)**:
   - Chỉ cho phép IP MikroTik Đà Nẵng (`116.110.212.30`) và IP nhà Kibe (`113.23.110.227`) kết nối vào dải port `5141..5158`.
   - Drop toàn bộ botnet và scanner bên ngoài tại card mạng.
4. **Kỷ luật kiểm chứng Math Assert chống báo cáo láo**:
   - BẮT BUỘC công thức toán học:
     $$\text{Số lượng IP Public độc lập} == \text{Số lượng cổng proxy}$$
   - Nếu $\ge 2$ cổng bị trùng IP: Tuyệt đối CẤM kết luận "LIVE" hay "ỔN ĐỊNH", bắt buộc FAIL-CLOSED và đưa máy vào diện `QUARANTINE`.
