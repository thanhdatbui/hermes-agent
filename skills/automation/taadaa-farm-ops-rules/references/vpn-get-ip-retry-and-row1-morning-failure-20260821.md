# VPN GET_IP Retry & Phân Tích Lỗi Ca Sáng Row 1 (2026-08-21)

## Bối cảnh
- Đêm 20/08 → sáng 21/08, ca sáng 06:00 (Lane B, Row 1) chạy `multi-machine-feed-session` trên 80 máy.
- Máy 4 bị dừng oan 17:36 (20/08) với lý do "ViChanger GET_IP failed (proxy dead/unreachable)" dù proxy mobi4 vẫn sống.
- 21/08 ca sáng: máy 33, 34, 36, 72, 73 dính `blocked-vichanger-vpn` — GET_IP broadcast trả `result=0` hoặc ADB timeout ×3, dù tun0 UP + connectivity CONNECTED.

## Root cause
- `am broadcast ... GET_IP` KHÔNG phải lúc nào cũng trả `result=200, data="<ip>"`:
  - ViChanger app bận / bị kill → broadcast không có receiver → `result=0`, không data.
  - ADB shell timeout khi 80 máy broadcast đồng loạt lúc 06:00 (thump ADB daemon).
- Kết quả `allowed=False` → block máy theo VPN gate (fail-closed đúng rule nhưng false-positive).

## Fix (automation-core `preflight.py`, 2 commits)
1. `5b1f077` — fail-closed guard: tun0 UP nhưng IP unverifiable → `allowed=False`.
2. `3a715bb` — retry 3 lần broadcast, sleep 2s giữa các lần; CHỈ block khi cả 3 fail:
```python
for attempt in range(1, 4):
    try:
        get_ip = adb.shell([...GET_IP...], timeout=timeout, check=False)
        out = _text(get_ip.stdout)
        match = re.search(r'data="([^"]+)"', out)
        if "result=200" in out and match and match.group(1).strip():
            proxy_ip = match.group(1).strip(); ip_verified = True; break
        ...
    except Exception as exc: ...
    time.sleep(2.0)
```
- **PITFALL:** phải `import time` — thiếu import → `NameError: name 'time' is not defined` (bắt được bởi test).
- **PITFALL:** test `test_mapped_device_blocks_when_vichanger_get_ip_fails` assert `"ViChanger GET_IP failed" in result.error` — error message phải chứa chuỗi này, giữ nguyên format cũ khi thêm retry.

## Chẩn đoán chéo "proxy dead" (làm TRƯỚC khi kết luận)
1. Test proxy từ PC:
```python
import requests
from urllib.parse import quote
proxy_url = f"http://{quote('mobi4')}:{quote('TaadaaMobi#2026!')}@test.taadaa.click:5104"
requests.get('http://api.ipify.org', proxies={'http': proxy_url, 'https': proxy_url}, timeout=12)
```
   RAW `http://mobi4:TaadaaMobi#2026!@host:port` → `InvalidURL` (# = fragment). BẮT BUỘC URL-encode `#`→`%23`, `!`→`%21`.
2. Device browser leak check:
```
adb shell am start -a android.intent.action.VIEW -d 'https://api.ipify.org'
adb exec-out screencap -p > ip.png   # vision_analyze đọc IP
```
3. IP PC == IP device → proxy SỐNG → lỗi là broadcast/ADB timeout, không phải proxy.
- Máy 4: proxy PC trả `27.69.65.12`, browser device cũng `27.69.65.12` → khớp → proxy sống.

## Đọc IP đúng cách qua broadcast
- ĐÚNG (có component, trả data): `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` → `result=200, data="27.69.65.12"`.
- SAI (thiếu `-n`): `am broadcast -a vn.vichanger.app.GET_IP` → `result=0`, không data → false "proxy dead".

## Phân tích lỗi ca sáng Row 1 (lane B, ngày lẻ)
- Manifest `assignment-v1-*.json`: entries có `account_row`, `slot_time`, `lane`, `status`. Máy 1 sáng = `lipsellczaw` row 1 (06:00/07:40/09:20), trưa = `tranngan767` row 3, tối = `lipsellczaw` row 1.
- Log `row-1-060047/.../log.jsonl` ghi `feed-session-smoke`:
  - `result: manual-needed`, error `popup is not in the shared TikTok allowlist; manual review required`, `swipes_completed: 0` → kẹt popup ngay TRƯỚC bước switcher → máy vẫn đứng nick cũ (máy 1 đứng `ginnyhanstei80` row 4 dù ca sáng là row 1).
  - `result: blocked-vichanger-vpn` → GET_IP fail → theo rule dừng hẳn, không lướt lộ IP.
- **Dạy học:** "ca sáng = row 1" là kỳ vọng từ manifest; máy đứng nick khác row khi popup lạ chặn trước switcher. Xem `references/device-lock-collision-and-recursive-grep-hang-20260820.md` cho collision botmail/hotmail.

## Đã verify
- pytest automation-core: `test_preflight.py` 9 passed → full suite 597 passed, push `3a715bb`.
- Proxy test PC máy 4: 200 → `27.69.65.12` khớp browser device.