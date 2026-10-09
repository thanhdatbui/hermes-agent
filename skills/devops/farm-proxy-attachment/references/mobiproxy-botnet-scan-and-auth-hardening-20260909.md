# MobiProxy Botnet Scan Attack & Auth IP Hardening (2026-09-09)

## Sự cố

Box OpenWrt MT7621 tại Thái Bình bị botnet Internet quét IP Viettel brute-force cổng proxy `5101..5138`:
- Bảng conntrack của chip MT7621 bị tràn ngập → CPU 100% → Nginx + PHP-FPM đồng loạt chết → `502 Bad Gateway` + mất DDNS.
- Toàn bộ 32 cổng bị báo DEAD trong log healer (`mobiproxy_stats.json`: `total_heals_attempted: 1525, total_heals_succeeded: 3`).
- Bên bán phải tắt NAT (`nat_port: 0`) để box hạ tải, dẫn đến farm mất proxy hoàn toàn.

## Phân tích root cause

1. **Cổng proxy mở toang cho toàn Internet** (`NAT: ANY source IP → 51xx`) không có firewall whitelist source IP.
2. **Bot scanner toàn cầu** (Shodan, Censys, botnet) quét dải IP `171.224.x.x / 117.1.x.x` Viettel, phát hiện cổng `5101..5138` → brute force pass → làm tràn conntrack.
3. **Cloudflare KHÔNG bảo vệ được** cổng proxy TCP 51xx — chỉ bảo vệ cổng web 80/443.
4. **Auto-healer (`mobiproxy_auto_healer.py`)** khi thấy port dead liên tục gọi `/proxy_recreat` → càng làm quá tải API backend của box vốn đã nghẽn.

## Giải pháp đã thực hiện

### Cấu hình Auth IP (`proxy.access` per-proxy hoặc `proxy.access_bulk`)

**Web UI:** `http://test.taadaa.click/#proxies` → click proxy → "Cấu hình truy cập"

**API chuẩn per-proxy (AN TOÀN):**
```python
POST /api.php?action=proxy.access
{
  "index": N,          # 1..40
  "mode": "iponly",    # hoặc "strong"
  "password": "TaadaaMobi#2026!",
  "allowed_ips": "42.119.145.61"
}
```

**API bulk (⚠️ NGUY HIỂM — xem Pitfall):**
```python
POST /api.php?action=proxy.access_bulk
{
  "mode": "strong",
  "password": "TaadaaMobi#2026!",
  "allowed_ips": "42.119.145.61"
}
# → Trả {"ok":true,"configs":40} NHƯNG restart 40 proxy đồng loạt → PHP OOM → 502
```

### Các chế độ xác thực

| Mode | Hoạt động | Đặc điểm |
|------|-----------|-----------|
| `none` | Không xác thực | Ai cũng vào được |
| `strong` | User/Pass (HTTP 407 nếu sai) | Kết hợp được với `allowed_ips` |
| `iponly` | Chặn theo source IP | Không cần pass, nhẹ hơn |

**Khuyến nghị:** `strong` + `allowed_ips` = 2 lớp bảo vệ, bot sai IP bị từ chối ngay tại proxy.

### Cấu trúc file config proxy trên box

Mỗi proxy được lưu tại `/usr/local/bin/proxyXX-6proxy.cfg` trên OpenWrt. Khi set qua API và hệ thống xác nhận `ok:true`, cấu hình **đã được ghi vào file disk** và **sẽ load lại sau reboot** dù PHP-FPM có bị kill.

### API quan trọng đã xác minh hoạt động

```
GET  /proxy_getlist?token=<mpx_token>    → Danh sách proxy + IP + uptime + status
GET  /api.php?action=dashboard           → Full config từng proxy (auth, allowed_ips, ports...)
GET  /api.php?action=settings.get        → Cấu hình system (nat_port, api_security...)
POST /api.php?action=proxy.nat           → {"enabled": true/false} — Bật/tắt NAT
POST /api.php?action=proxy.access        → Set auth cho 1 proxy
POST /api.php?action=proxy.access_bulk   → ⚠️ Set auth cho tất cả (NGUY HIỂM với MT7621)
POST /api.php?action=settings.api_security → {"enabled": true/false} — Bật/tắt Bearer token
GET  /api.php?action=audit.list          → Log đăng nhập web admin
```

**Login flow (CSRF bắt buộc 2 bước):**
```python
# B1: GET login.php → lấy _csrf
csrf_login = re.search(r'name="_csrf"\s+value="([^"]+)"', html).group(1)
# B2: POST login → lấy session cookie
urllib.parse.urlencode({'_csrf': csrf_login, 'password': PASSWORD})
# B3: GET index.php → lấy csrf-token meta (dành cho API POST)
csrf_api = re.search(r'name="csrf-token"\s+content="([^"]+)"', html_idx).group(1)
# B4: POST API với header X-CSRF-Token: csrf_api + X-Requested-With: XMLHttpRequest
```

## IP hiện tại nhà Kibe (FPT)

- **Direct IP:** `42.119.145.61` — IP FPT của máy Kibe, dùng làm whitelist `allowed_ips`.
- **Lưu ý:** FPT có thể đổi IP khi modem reboot. Khi bị mất proxy đột ngột nên check lại IP FPT (`curl https://api.ipify.org`) và cập nhật whitelist nếu cần.

## Quy trình khẩn cấp khi box bị botnet sập

1. **Pause ngay cron healer:** `hermes cron pause mobiproxy-auto-healer-watchdog`
2. **Kệ box tự nghỉ** (không probe, không gọi API).
3. Khi web 80 mở lại nhưng PHP vẫn 502: **Cần reboot box** (rút nguồn hoặc SSH → `/etc/init.d/php7-fpm restart`).
4. Sau khi box live: Canh web watchdog **interval 120s** (không dưới 2 phút).
5. Khi web đã ổn định: Set auth từng proxy **thủ công từng cái qua web UI**, không dùng `access_bulk`.
6. **Bật lại cron healer** sau khi proxy đã ổn định hoàn toàn.

## Tính năng "Bật Interface" trên web

- **Bật interface** = `ifup pppoe-proxyXX` → Kích con box quay số PPPoE lại để lấy IP mới.
- **Tắt interface** = `ifdown pppoe-proxyXX` → Ngắt hẳn kết nối PPPoE của cổng đó.
- **Khác với Reset IP:** Reset IP = đổi IP trong khi interface vẫn UP. Bật interface = mở lại interface đang DOWN.
