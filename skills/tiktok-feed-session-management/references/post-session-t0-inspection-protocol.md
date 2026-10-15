# Post-Session T0 Inspection Protocol (After Watchdog Cronjob Report)

## Trigger
When `tiktok-feed-session-watchdog` Cronjob Response arrives, execute ALL steps in order
before drawing conclusions or escalating.

---

## Step 1: Check Device Locks (Orphan Detection)

```bash
python "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py" --dry-run
```

Interpret output:
- `REAPED N dead-owner / expired locks` → orphan locks cleaned (or would be cleaned)
- `KEPT N ... running_active pid=...` → live batch still running; do NOT interrupt
- `machine_N.lock.json (running_active ...)` → which machines are legitimately locked

**Cross-check active PIDs** when status is ambiguous:
```python
import psutil
for pid in [PID1, PID2, ...]:
    print(pid, psutil.pid_exists(pid))
```

If a lock shows `running_active` but PID is dead → orphan; flag it.
The `reap-dead-owner-locks` cron (`b63730cc5c85`, runs every 5 min) will auto-clean it.

---

## Step 2: Check Live ADB Device Status

```bash
python D:/Taadaa/tools/inspect_machine.py
```

(no machine number = list all devices both local and Admin remote)

Key things to check:
- Kibe local: how many `device` vs `offline`/`not found`
- Admin remote (192.168.110.119:5037): same
- Offline serials → correlate with machines that had ADB errors in the report

---

## Step 3: Check Runtime Summary for Current Session

```python
import os
p = 'D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/row-N-HHMMSS'
runs = os.listdir(p)
print(runs)
```

Then per-machine stop_reason distribution:
```python
import os
from collections import Counter
reasons = Counter()
machines_dir = 'D:/Taadaa/runtime/<cluster>/live/<date>/<row-run>/<session>/machines'
for m in os.listdir(machines_dir):
    sub = os.path.join(machines_dir, m)
    for run in os.listdir(sub):
        sm = os.path.join(sub, run, 'summary.txt')
        if os.path.exists(sm):
            with open(sm, encoding='utf-8') as f:
                for line in f:
                    if line.startswith('stop_reason:'):
                        reasons[line.split(':', 1)[1].strip()] += 1
                        break
for r, c in reasons.most_common():
    print(f'{c}x: {r}')
```

**Runtime directory layout:**
- `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/`  ← Kibe cluster (M1-80)
- `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/` ← Admin cluster (M201-280)
- `row-1-HHMMSS` = Row 1 (Tik1), `row-2-HHMMSS` = Row 2, etc.
- Inner `YYYYMMDD-HHMMSS/` = actual session run folder
- `machines/machine_N/<session>/summary.txt` = per-device verdict

**Find failed machines only (filter out success):**
```python
for m in sorted(os.listdir(machines_dir), key=lambda x: int(x.replace('machine_', '')) if x.replace('machine_', '').isdigit() else 999):
    sub = os.path.join(machines_dir, m)
    for run in os.listdir(sub):
        sm = os.path.join(sub, run, 'summary.txt')
        if os.path.exists(sm):
            with open(sm, encoding='utf-8') as f:
                content = f.read()
                sr = 'unknown'
                for line in content.splitlines():
                    if line.startswith('stop_reason:'):
                        sr = line.split(':', 1)[1].strip()
                        break
                if 'feed-session-smoke completed' not in sr and 'full swipes completed' not in sr:
                    print(f'M{m}: {sr}')
```

---

## Step 4: Correlate & Classify

Map stop_reasons to the 6 categories in the Telegram watchdog report:
| stop_reason prefix | Watchdog category |
|---|---|
| `device is offline or ADB/USB disconnected` | Mất kết nối ADB/USB |
| `adb command timed out` | Mất kết nối ADB/USB (timeout sub-type) |
| `Device serial '...' was not found` | Mất kết nối ADB/USB |
| `required router proxy is unreachable` → `Wi-Fi not connected` | Mất kết nối Wi-Fi (AP) |
| `prepare-tiktok failed to focus TikTok after launch` | Lỗi App TikTok/Script |
| `TikTok focus lost after navigation tap` | Lỗi App TikTok/Script |
| `focused package unavailable` | Lỗi App TikTok/Script |
| `ATX_SESSION_UNAVAILABLE` | Lỗi App TikTok/Script |
| `navigation target profile not found in XML` | Lỗi App TikTok/Script |
| `screen capture invalid; feed not confirmed` | Lỗi App TikTok/Script |
| `feed swipe command failed` | Lỗi App TikTok/Script |
| `startup ad/splash marker detected` | Lỗi App TikTok/Script |
| `unknown TikTok state` | Lỗi App TikTok/Script |

---

## Step 5: Determine Action

| Condition | Action |
|---|---|
| ADB socket timeout on concurrent startup (≥5 machines same sub-type) | TRANSIENT — no code fix needed; next session will self-recover |
| Hardware offline (`device not found`, `device offline`) | Physical USB or power issue; note machine number, no action needed by Coordinator |
| Wi-Fi loss (M7-type) | `farm-wifi-auto-healer` watchdog handles auto-reconnect |
| App focus loss ≤20% of machines | TRANSIENT — S7 memory pressure settled by next Phiên |
| App focus loss >40% of machines or same machines repeating across Phiên 1 AND Phiên 2 | Investigate `inspect_machine.py N`; potential code fix needed |
| `ATX_SESSION_UNAVAILABLE` isolated (<5 machines) | TRANSIENT — atx-agent reset |
| `ATX_SESSION_UNAVAILABLE` widespread >10 machines | Investigate atx-agent health on the cluster host |

---

## Anti-Patterns (Invariants)

- **CẤM** `os.walk`, `glob(recursive=True)`, `find`, or `grep -r` to locate log files
- **CẤM** reading runtime directories via `search_files` broad scan
- **ONLY** read `summary.txt` inside already-known session directory
- Session directories are always deterministic: `/runtime/<cluster>/live/<date>/<row-run>/<YYYYMMDD-HHMMSS>/`
- Always check BOTH clusters (kibe + admin) when the watchdog report covers both farms
