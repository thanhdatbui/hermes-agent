# Multi-Cluster Date Scan Parity & Host Isolation Discrimination

## 1. Multi-Cluster Date Scan Parity (Anti-Local Blindness)

### Problem
A multi-cluster session watchdog (e.g., `feed_session_watchdog.py`) monitors multiple clusters (`CLUSTERS = [kibe, admin]`).
If `all_date_dirs` only scrapes dates from the controller's local runtime path (`LIVE_ROOT = D:\Taadaa\runtime\kibe\live`), any transient delay or disruption on the local host (such as an adb port collision or preflight skip) prevents the local date folder (`YYYY-MM-DD`) from being created.
Consequently, the watchdog filters out `today` from `dates_to_check`, completely blinding itself to remote clusters (`admin`) that ran on time and finished successfully. Telemetry is suppressed, and operators receive zero shift reports.

### Invariant Contract
1. **Always Include Today:** `all_date_dirs` MUST explicitly include `today` regardless of whether any directory exists yet on disk.
2. **Cluster Directory Union:** Build candidate dates by taking the set union of all active clusters' `live_root` paths within the retention cutoff:
   ```python
   all_date_dirs = set()
   for cl in CLUSTERS:
       cl_live = cl.get("live_root")
       if cl_live and os.path.exists(cl_live):
           for d in os.listdir(cl_live):
               if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= retention_cutoff and os.path.isdir(os.path.join(cl_live, d)):
                   all_date_dirs.add(d)
   all_date_dirs.add(today)
   dates_to_check = [(d, d == today) for d in sorted(all_date_dirs)]
   ```

---

## 2. Desktop Control Tool Port Listener vs Device Claim Discrimination

### Problem
Tools like XiaoWei (Tiểu Vi), Total Control, or custom mirroring apps start a background daemon (`tools/adb.exe -P 5038 nodaemon server start`) that listens on an alternate port (5038).
An over-engineered preflight gate checking `Get-NetTCPConnection -LocalPort 5038 -State Listen` assumes that an open port means *all* farm devices are seized, throwing a fatal exception (`PREFLIGHT_PORT_5038_BLOCKED`) and aborting the entire 80-device session.
In reality:
- XiaoWei's daemon listens on 5038 in an idle state without automatically claiming USB handles (`adb -P 5038 devices` returns an empty list).
- Farm ADB (port 5037) retains uninterrupted control of all connected devices (`adb devices` returns 78 devices).
- The user is often using XiaoWei on a single locked device for manual tasks (e.g. placing orders) while the other 79 devices are idle and ready to nurture.

### Invariant Contract
1. **Never Fail-Closed on Idle Listening Ports:** Do not abort the entire batch runner simply because an alternate tool's port is open.
2. **Rely on Fine-Grained Device Locks:** Rely on per-machine device locks (`machine_<M>.lock.json`) to skip devices actively operated by the user, while allowing the rest of the fleet to proceed concurrently:
   ```powershell
   if (-not (Clear-XiaoWeiPort5038)) {
       Write-Warning "PREFLIGHT_PORT_5038_ACTIVE: Port 5038 is occupied by XiaoWei. Proceeding with feed session; individual device locks will protect active user devices."
   }
   ```
3. **Verify with Ground-Truth Probes:** Probe both ADB daemons (`-P 5038 devices` vs `-P 5037 devices`) before concluding that device handles are seized.
