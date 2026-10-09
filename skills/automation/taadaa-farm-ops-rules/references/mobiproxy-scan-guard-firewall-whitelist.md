# MobiProxy Scan Guard Firewall Whitelist (Firmware 3.0.67+)

## Background
- MobiProxy R3G v1 (MT7621, 256MB RAM) chạy firmware 3.0.67+ có thêm tính năng **Scan Guard** — tường lửa iptables ở kernel level.
- Thay thế cơ chế NAT thủ công + whitelist ở tầng PHP (gây spike RAM → sập 502 khi update hàng loạt).

## Cách hoạt động
1. **API endpoint**: `POST /api.php?action=proxy.scan_guard.save`
2. **Payload**: JSON `{enabled: true, allowed_ips: "IP1\nIP2\n"}` + header `X-CSRF-Token` + cookie session
3. **Xử lý**: Box ghi rule iptables `DROP` cho các IP không nằm trong whitelist **trước khi** gói tin chạm vào daemon proxy/PHP
4. **Không restart 40 tiến trình proxy**, không spike RAM, web không bị 502

## IP cần whitelist
- **IP WAN MikroTik** (động, PPPoE): ví dụ `171.231.195.2` — dùng cho 32 cổng proxy farm
- **IP PC Kibe** (FPT): ví dụ `42.118.214.93` — truy cập web admin

## Hành động vận hành
- Khi MikroTik đổi IP WAN (PPPoE quay số): chỉ cần gọi API `proxy.scan_guard.save` với IP mới → cập nhật trong <1s, **không tắt NAT**, không sập box
- **PAUSE cron `mobiproxy-auto-healer-watchdog`** (Job ID `7e5e3980dde1`) khi Scan Guard đang hoạt động — cron này dùng logic cũ (tắt NAT → update → bật NAT) gây sập 502

## Test thực tế (11/09/2026)
- 32/32 cổng proxy (5101–5138): **THÔNG 100%**, ~0.45s/request
- Web admin: HTTP 200 load ~1s, **không 502**
- 79 máy S7 online: TikTok feed session chạy OK qua MobiProxy