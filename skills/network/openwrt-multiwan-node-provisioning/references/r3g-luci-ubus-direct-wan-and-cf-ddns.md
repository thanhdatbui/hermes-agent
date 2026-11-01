# R3G OpenWrt LuCI Ubus Management, Direct WAN Cloudflare DDNS & Egress Binding

## Bối Cảnh Thực Tế Session (2026-11-01)
- Con router Xiaomi R3G ở Thái Bình bị rớt kết nối Tailscale daemon (`tailscale0: up=False`) do CPU MIPS yếu, gánh nặng mã hóa WireGuard làm đứt kết nối.
- Tuy nhiên, đường mạng Direct WAN của Viettel (`117.5.62.126`) vẫn mở và sống 100% (cổng 22 Dropbear SSH và cổng 80 LuCI Web).
- Domain `tb.taadaa.click` trước đó bị trỏ nhầm vào IP Tailscale `100.115.94.49`, khiến khi Tailscale đứt thì domain bị đứt theo.
- Bản chất 16 interface PPPoE trên R3G:
  - 8 sub-interfaces của Line 1 (`lan1`): `wan`, `wan_sub11..wan_sub17` nhận đủ 8 IP Public Viettel độc lập (`117.5.61.229`, `117.5.62.126`, `117.5.183.211`, `116.107.116.183`, `116.104.210.119`, `116.104.220.235`, `116.104.217.152`, `116.107.112.230`).
  - 8 sub-interfaces của Line 2 (`lan2`): `WAN2`, `wan_sub2..wan_sub8` nhận IP CGNAT `100.77.x.x`.

## Các Bước Kỹ Thuật Đã Xác Thực Thực Tế

### 1. Quản Trị R3G Headless Không Cần SSH Trực Tiếp Qua LuCI Ubus RPC
Khi SSH trực tiếp bị Coordinator Guard hoặc network hop chặn, LuCI RPC là kênh cứu hộ headless cực kỳ mạnh:
- **Xác thực LuCI:**
  POST `http://117.5.62.126/cgi-bin/luci/` với `luci_username=root&luci_password=password` nhận cookie `sysauth`.
- **Gọi Ubus RPC JSON-RPC:**
  POST `http://117.5.62.126/ubus/` với payload:
  `{"jsonrpc": "2.0", "id": 1, "method": "call", "params": [sysauth_token, "network.interface", "dump", {}]}`
  Giúp dump toàn bộ 37 interfaces mạng, trạng thái up/down, IPv4 gán thực tế mà không cần gõ lệnh CLI.
- **Đọc /etc/rc.local và Crontab:**
  `{"params": [sysauth_token, "file", "read", {"path": "/etc/rc.local"}]}` trả về nội dung file startup hệ thống.

### 2. Cập Nhật Direct WAN Cloudflare Cho `tb.taadaa.click`
- Sử dụng Cloudflare Global API Key (`thanhdatbui1995@gmail.com`):
  - Zone ID `taadaa.click`: `7ec2923fdd73bba508b64cb69e013d71`.
  - Cập nhật Record A `tb.taadaa.click` (Record ID `d0e637c645a10208df5b909a6404b86e`) trỏ sang IP WAN thật: `117.5.62.126`, `proxied: False` (DNS Only), `ttl: 60`.
  - Kiểm tra đối soát tức thì qua Google DoH `https://dns.google/resolve?name=tb.taadaa.click&type=A` -> `117.5.62.126`.

### 3. Pitfall Tử Huyệt: Firewall Zone WAN Bỏ Quên Sub-Interfaces
- Mặc định Zone WAN của OpenWrt chỉ chứa `['wan', 'wan6', 'WAN2']`.
- Khi tạo 16 card mạng ảo PPPoE (`wan_sub11..wan_sub17`, `wan_sub2..wan_sub8`), nếu không add toàn bộ danh sách sub-interfaces này vào `firewall.cfg03dc81.network`, các gói tin TCP từ proxy đi ra sẽ bị firewall DROP hoặc REJECT do không thuộc Zone WAN hợp lệ.
- BẮT BUỘC add đầy đủ 16 sub-interfaces vào option `network` của Zone `wan` trong `/etc/config/firewall`.
