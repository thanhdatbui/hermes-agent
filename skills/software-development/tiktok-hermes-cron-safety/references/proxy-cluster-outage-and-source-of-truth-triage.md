# Proxy Cluster Outage & Single Source of Truth Triage (2026-08-28)

## 1. Single Source of Truth: `taikhoan_run_safe.xlsx` vs Inferred/Auxiliary Files

- **Invariant:** `taikhoan_run_safe.xlsx` (`Accounts` sheet) is the **authoritative truth** for account inventory, physical row assignments, and device bindings.
- **Date String in Device ID Pitfall:**
  - When manual edits or legacy reg deferrals place dates (`23/08/2026`, `2026-08-23`) into the `Device ID` column (column 2) instead of the hardware serial:
    - `picker.py` or inventory detectors will skip the row or flag `CAPACITY_EXCEEDED` / missing hardware serial.
    - **Agent Pitfall:** DO NOT claim to the user that the account "does not exist" or "missing ID". The account ID is present in column 3 (`ID`), but the hardware serial is malformed.
    - **Fix:** Normalize the serial in column 2 from the machine's canonical hardware serial (e.g. `ce12160c75f16b2605` for Machine 73) derived from other rows of the same machine or `PROXYgandienthoai.xlsx`. Sync to `Tik<row>.xlsx` and re-run.

## 2. Proxy Cluster Outage Triage (`test.taadaa.click` vs `mirotik1.taadaa.click`)

- **Symptom:** User notices no session summary reported for a scheduled ca (e.g. Ca 1 - Row 2) or asks why machines didn't run when proxy is down.
- **Root Cause & Verification Sequence:**
  1. **Test Port Reachability:** Probe proxy host ports directly:
     ```python
     import socket
     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     s.settimeout(3.0)
     res = s.connect_ex(('test.taadaa.click', 10001)) # 0 = OPEN, 10035/refused = DOWN
     ```
  2. **Check Farm Proxy Distribution:** Read `PROXYgandienthoai.xlsx`. A majority of machines (e.g. 64/80) may be routed through `test.taadaa.click`.
  3. **Cron Invocation vs Device Execution:**
     - Cron `tiktok_runner` **DID invoke and spawn** the PowerShell launcher (`run-feed-session.ps1 -Run`).
     - **Fail-Closed VPN Preflight (`require_vichanger_connected`):** Each worker attempts VPN reconnect/readiness check. When the proxy is unreachable, it raises `TimeoutError: proxy readiness timed out` after retries, marking the target `blocked-vichanger-vpn` with **0 swipes completed**.
     - **Zero Swipes Guarantee:** TikTok is NEVER opened on raw/direct internet IP (protecting accounts from direct IP shadowban/checkpoint).
  4. **Queue Starvation on Mixed Proxy Pools:**
     - Because `run_tiktok.py --mode multi-machine-feed-session` runs up to 40 concurrent workers with random staggered delays across all 72 due machines:
     - Workers stuck retrying dead proxies (from `test.taadaa.click`) hold concurrency slots and delay processing. If the entire session window expires, even machines on working proxies (`mirotik1.taadaa.click`) may remain queued or incomplete.
     - Result: `published_machines` in the cohort remains `0/72`.

## 3. Clear Reporting Language to User

- When asked "Cron sáng nay có gọi máy chạy không khi proxy lỗi?":
  - Explicitly answer: **Cron CÓ gọi tiến trình**, nhưng **toàn bộ máy thuộc proxy lỗi đều bị chặn an toàn tại preflight VPN (`blocked-vichanger-vpn`) với 0 lượt vuốt (0 swipes)**.
  - State clearly that no video was browsed on direct IP, and report the exact count of affected vs working proxy machines.
