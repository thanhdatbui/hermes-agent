# Batch Alert Log Triage — Pitfalls & Patterns (2026-09-21)

## 1. Log batch multi-machine KHÔNG nằm trong `.ai-runs/`

| Sai | Đúng |
|-----|------|
| `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/20260921-*/log.jsonl` | `D:/Taadaa/runtime/kibe/live/<date>/row-<N>-<HHMM>/<session>/` |

### Cấu trúc đúng:
```
D:/Taadaa/runtime/kibe/live/2026-09-21/row-5-200304/20260921-200552/
  summary.txt                  ← tổng hợp toàn batch, blocker_taxonomy_summary
  run_manifest.json            ← đầy đủ final_status/blocker_type/stop_reason từng máy
  log.jsonl                    ← event log batch-level
  machines/machine_<N>/<session>/
    log.jsonl                  ← log chi tiết máy N
    summary.txt                ← summary máy N
```

### Tìm thư mục batch:
1. Xem cron output `cdd43b124363` (phase9-runner-tiktok-feed) → tìm dòng `spawned Row<N> pid=...` → lấy timestamp HH:MM
2. `ls D:/Taadaa/runtime/kibe/live/<date>/` → khớp `row-<N>-<HHMM>`

## 2. Batch Alert taxonomy label ≠ lỗi thực từng máy

Alert format: `detector-miss:network/error/retry marker detected` là **label taxonomy tổng hợp** của watchdog script, NOT lỗi đồng nhất tất cả máy.

**Quy trình đúng:**
```
run_manifest.json → machines[] → blocker_type + stop_reason từng máy
```

### Ví dụ thực (Ca 3 Phiên 1, 2026-09-21):
Cùng 1 batch alert "detector-miss" nhưng thực ra:

| Máy | blocker_type | stop_reason | Fix |
|-----|-------------|-------------|-----|
| M76, M80 | detector-miss | network/error/retry marker detected | Mạng 4G thoáng qua, tự hồi phục |
| M74 | detector-miss | unknown TikTok state; swipe recovery (2 swipes) still stuck | Màn hình lạ, cần inspect |
| M62 | detector-miss | startup ad/splash marker detected | Force-stop TikTok |
| M73 | script-blocker | known TikTok screen | Script dừng sớm bất thường |
| M9 | script-blocker | blocked-proxy-vpn | Restart ViChanger |
| M10, M30 | focus/device issue | device 'xxx' not found | Cắm lại USB |
| M19 | focus/device issue | config-error | Lỗi config máy |

## 3. inspect_machine.py: cú pháp đúng

```bash
# ĐÚNG
python D:/Taadaa/tools/inspect_machine.py 12
# Hoặc batch loop
for m in 8 9 10 19 30; do python D:/Taadaa/tools/inspect_machine.py $m; echo "---"; done

# SAI — không nhận prefix "M"
python D:/Taadaa/tools/inspect_machine.py M12
```

## 4. Phân loại lỗi fix được vs cần điều tra

### Fix được ngay (không cần patch code):
- **ADB offline** (`device not found`): cắm lại USB hoặc `adb reconnect`
- **VPN preflight** (`blocked-proxy-vpn`): restart ViChanger/VPN trên máy
- **Splash ad stuck**: `adb shell am force-stop com.ss.android.ugc.trill`
- **Network spike** (thoáng qua): tự hồi phục phiên sau, không cần can thiệp

### Cần inspect thêm (xem log.jsonl của máy đó):
- `unknown TikTok state` — màn hình lạ, cần screencap + XML dump
- `known TikTok screen` với swipes_completed=0 — script dừng sớm bất thường
- `config-error` — lỗi mapping Excel/config máy

## 5. Kiểm tra proxy từ PC (không cần proxy socks5 lib):

```python
import urllib.request
proxy_url = f'http://{user}:{pass_encoded}@{host}:{port}'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy_url}))
with opener.open('http://httpbin.org/ip', timeout=5) as r:
    print(r.read().decode())
```
Dùng `httpbin.org/ip` thay vì `api.ipify.org` — ipify trả 502 với một số proxy config.
