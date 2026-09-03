# Khommo247 VPS cron attempt (2026-08-20)

Mục tiêu user: "cron tự check live TikTok mỗi ngày 1 lần, chạy trên VPS, không cần mở máy nhà" — dùng khommo247 login thật (user sẵn sàng cấp tài khoản).

## Kết quả: BẾ TẮC nếu chỉ có IP datacenter — cần proxy IP sạch VPS kết nối được

## Trình tự đã làm trên VPS (152.42.187.200, Ubuntu 22.04, 1 core / 2GB RAM / 49GB)

1. **Cài Xvfb + deps**: `apt-get install -y xvfb x11-utils libxcomposite1 libasound2 libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libfontconfig1 libgbm1 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libxrandr2 libxss1 libxtst6 wmctrl` → OK.
2. **Cài venv + Camoufox**: 
   - Pitfall: `apt-get install python3-venv` thiếu → `python3 -m venv` fail "ensurepip is not available". Cài `python3.10-venv python3-pip` trước.
   - Pitfall: dpkg lock (`/var/lib/dpkg/lock-frontend`) — apt install trước đó (Xvfb) chưa dứt hẳn hoặc có process khác. Chờ: `for i in $(seq 1 30); do fuser /var/lib/dpkg/lock-frontend || break; sleep 2; done`.
   - `python3 -m venv /opt/camoufox-venv; source .../bin/activate; pip install "camoufox[geoip]" playwright; python -m camoufox fetch` → OK (venv tại `/opt/camoufox-venv`).
3. **Chạy Camoufox headful trên display ảo**: `cd /opt && source /opt/camoufox-venv/bin/activate && xvfb-run -a python /opt/test_xxx.py` — **Camoufox headful từ IP VPS datacenter VẪN BỊ Cloudflare chặn** "Just a moment..." (title không bao giờ rời khỏi challenge, dù chờ 60s+).
   - Đối chiếu: Camoufox headful từ IP NHÀ (máy Kibe) qua CF sau ~8s vào thẳng tool page. → **IP reputation quyết định, browser fingerprint không cứu được khi IP datacenter bị sờ gáy.**

## Proxy farm `test.taadaa.click` (từ PROXYgandienthoai.xlsx)

- Format: `test.taadaa.click:5101:mobi1:TaadaaMobi#2026!` — 185 dòng (5101..5180), user `mobiN`.
- **Pitfall password chứa `#`**: Camoufox/playwright parse proxy URL string fail nếu để raw: `Failed to parse: http://mobi1:TaadaaMobi#2026!@test.taadaa.click:5101`. Fix: `enc = urllib.parse.quote("TaadaaMobi#2026!", safe="")` → server `http://mobi1:{enc}@test.taadaa.click:5101` (hoặc truyền object `{"server": ..., "username": ..., "password": ...}` — password trong object không cần encode; chỉ cần encode khi nhét vào URL string).
- **Proxy farm không route từ VPS**: từ máy nhà (`urllib` qua proxy `http://mobi1:%23...@test.taadaa.click:5101`) trả IP mobile `27.69.64.218` OK; từ VPS Camoufox/proxy → `NS_ERROR_PROXY_CONNECTION_REFUSED` (kể cả geoip=True). Kết luận: farm giới hạn theo IP nguồn (chặn datacenter VPS) — muốn VPS dùng phải whitelist IP `152.42.187.200` trong farm, hoặc dùng proxy mua riêng có IP sạch VPS kết nối được.

## Lựa chọn thực tế còn lại cho cron check TikTok

- **A. Giữ VPS direct check TikTok** (`tiktok-direct-vps-checklive-2026-08.md`): KHÔNG cần login/proxy/browser — tiktok.com trả 200 từ IP datacenter SGP, parse `__UNIVERSAL_DATA_FOR_REHYDRATION__` statusCode 0/10221, retry 8-12, chỉ còn ~2% UNKNOWN. Không dính CF login gate.
- **B. Cron qua khommo247**: cần (1) tài khoản login thật, (2) Camoufox headful (hoặc CDP) chạy ở đâu đó có IP sạch — nếu chỉ có VPS datacenter thì phải thêm proxy IP sạch route được; nếu chấp nhận máy nhà bật thì chạy Windows Task Scheduler (không cần user thao tác hàng ngày nhưng máy phải bật).

## Setup Xvfb on VPS (gọn để tái sử dụng)

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq xvfb python3.10-venv python3-pip
python3 -m venv /opt/camoufox-venv
source /opt/camoufox-venv/bin/activate
pip install -q "camoufox[geoip]" playwright
python -m camoufox fetch
# chạy headful ảo:
xvfb-run -a python /opt/script.py
```