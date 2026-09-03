# Live-check session 2026-08-05 (machine 1 → ALIVE)

Verified `check_mailbox_alive` on a real device + real mail. Exact transcript of what worked and what didn't.

## Candidate inventory (read-only)

- `gmail_clean_v2.xlsx` (D:\OneDrive\codex_gmail_debug\register gmail\), sheet `Gmail Accounts` (291 rows), header: `số máy | tài khoản gmail | pass mail | 2fa | mail khôi phục | ngày tháng năm sinh | ngày tạo | mã phụ hồi`.
- ~31 hotmail/outlook rows across 26 machines; all serials resolve from `taikhoan_run_safe.xlsx` sheet `Accounts`; 80 devices online.
- Machine 1 has TWO hotmail rows: row 3 `lipseybaroua@hotmail.com` (old, 2026-02-27) + row 4 `GinnyHanstein8045@hotmail.com` (new, ngày tạo 2026-08-02). User: **use the bottom (newest) row**.

## What failed and why

| Attempt | Result | Root cause |
|---|---|---|
| `lipseybaroua@hotmail.com` (row 3) | UNKNOWN (`LoginBlocked: Could not identify Outlook password field`) | Chrome session on machine 1 held a different account; machine stuck in RecentsActivity overlay; WebView exposed only `url_bar` |
| Reset machine (force-stop launcher, re-open Chrome) | same UNKNOWN | accessibility OFF → WebView hierarchy empty |
| `GinnyHanstein8045@hotmail.com` (row 4) after clean reset | **ALIVE** | login `SUCCESS`; artifact `login_20260805_110723.json` |

## Commands that worked

```bash
# VPN for machine 1
cd /d/Taadaa/gan-proxy && python scripts/gan_proxy_fleet.py run --machines 1 --workers 1 --timeout 45
# → machine=1 status=SUCCESS elapsed=12.02s

# Verify VPN
adb -s <serial> shell "ip addr show tun0"   # tun0 UP
adb -s <serial> shell "dumpsys connectivity" | grep "VPN.*CONNECTED"

# Live check
cd /d/Taadaa/Hotmail && PYTHONPATH=. python -u -c "
from pathlib import Path
from flows.hotmail_login import check_mailbox_alive, resolve_adb
print(check_mailbox_alive(resolve_adb(None), '<serial>', '<email>', '<pass>', Path('.ai-runs')/'live-check-20260805'))
"
# → ALIVE

# Debug traceback (unwrap the try/except)
python -u -c "
from pathlib import Path
from flows.hotmail_login import login, resolve_adb
try: print(login(resolve_adb(None), '<serial>', '<email>', '<pass>', Path('.'), force_login=False))
except Exception: import traceback; traceback.print_exc()
"
```

## Machine state quirks observed

- 34 of ~37 lock files are `handoff` with **dead PIDs** — farm pattern; a lock file with dead PID is stale, safe to delete before re-running (but only after tasklist confirms PID gone).
- Lock stale + gan-proxy → `SKIPPED_DEVICE_LOCKED` → change-info pipeline fails `VPN_PROVIDER_RESULT_NOT_VERIFIED`. Delete `machine_<n>.lock.json` + `serial_<serial>.lock.json` after PID-death confirmation, then re-run.
- `accessibility_enabled=0` on every checked machine; `enabled_accessibility_services=null`; TalkBack service absent (`pm list services` empty). `uiautomator dump` → 0 nodes on Chrome 138. Only `url_bar` visible via `ui_xml`.
- Keep-signed-in "Có/Yes" button on 1080x1920: blue button region x=[80,1000] y=[1000,1680], centroid `(540,1593)`; tapping it passed the prompt (URL proof `outlook.live.com/mail/0/inbox`).
- Machine 30 change-info run: VPN verified `connected` ✓, login reached keep-signed-in, failed `LOGIN_BLOCKED: Could not select Keep me signed in: Yes` (semantic tap_text can't see the button in empty hierarchy). Coordinate tap resolved it manually.

## change-info pipeline transcript (machine 30, mail susannemortimerabby9@hotmail.com)

- Gate: `eligible=True` (age 15d, evidence from `.ai-runs/hotmail-machine-30-20260721/result_machine_30_account_1.json`).
- Command: `HOTMAIL_NEW_PASSWORD=<pw> PYTHONPATH=. python -u flows/hotmail_change_info.py --email <email> --machine 30 --live --artifacts .ai-runs/hotmail-change-info`
- First run: `VPN_PROVIDER_RESULT_NOT_VERIFIED` (lock stale → gan-proxy SKIPPED_DEVICE_LOCKED). After cleaning locks: VPN `connected`, then `LOGIN_BLOCKED` at keep-signed-in.
- 4 mails with evidence (eligible): susannemortimerabby9@hotmail.com (m30, SUCCESS), krystalsophroniaadonis7@hotmail.com (m30, RECOVERED_SUCCESS), florencenaomierayven6@hotmail.com (m38, RECOVERED_SUCCESS), eulaliaphilomenaclementina7@hotmail.com (m54, RECOVERED_SUCCESS) — all from 2026-07-21 runs.
- Gate breakdown across farm: LOGIN_DATE_UNVERIFIED 24, LOGIN_DATE_MISSING_OR_INVALID 4, LOGIN_TOO_RECENT 2, PASSWORD_MISSING 1.
