# Triage Hiện Trường: MobiProxy WAN Timeout Gây Lệch Port 20001-20038 & Fail-Closed Preflight (2026-11-06)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm (`night_2fa_trace_2026-11-06.log`): 47 máy cụm Kibe thất bại đồng loạt với lý do `ConsumerPreflightError`.
- Khi probe trực tiếp máy 3 (serial `9885e6344655484754`):
  `global proxy (192.168.110.2:20003) egress IP verification failed: dial tcp 192.168.110.2:20003: i/o timeout`

## 2. Bản Chất Kiến Trúc
1. **Phân bổ Port trên MikroTik (`192.168.110.2`):**
   - Dải `20001..20038`: Cấu hình Kernel DNAT trỏ sang IP WAN MobiProxy `116.107.124.158` (ports `5101..5138`).
   - Dải `20039..20080` và cụm sau: Đi qua rule Singbox container (`172.17.0.2`).
2. **Sự Cố Lệch Đường Truyền:**
   - Khi MobiProxy box bị ngắt kết nối vật lý, rớt PPPoE hoặc DDNS `test.taadaa.click` chưa cập nhật IP mới: toàn bộ kết nối tới `192.168.110.2:20001..20038` đều dính `i/o timeout`.
   - Các máy M39+ (như M46, M71, M72, M74, M76) đi qua Singbox vẫn chạy thành công 100%.
   - Các máy M32–M38 có interface VPN cục bộ `tun0` (ViChanger) UP vẫn pass preflight.
3. **Ý Nghĩa An Toàn Của `ConsumerPreflightError`:**
   - Đây là cơ chế `Fail-Closed` chuẩn của `require_android_vpn`.
   - Khi proxy ngắt, TikTok thường có cơ chế `Fail-Open` lén bypass qua Gateway Ruijie (`.1`) để ăn IP gốc nhà mạng (`113.23.110.227`). Preflight phát hiện timeout và chủ động dừng máy, bảo vệ danh tính dàn tài khoản farm.
