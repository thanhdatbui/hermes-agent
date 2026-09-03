# gan-proxy watcher ops — restart, mapping update, and reboot auto-assign test

Session-proven recipe (2026-08-12, machine 30) for operating the `gan-proxy` proxy
watcher stack on the farm host. Sanitized: never print serials/proxy values; use
SHA-256 serial hash prefixes in evidence.

## Stack layout (who respawns whom)

- Scheduled Task `GanProxyWatcherTray` (logon, Enabled/Running):
  `powershell -STA -WindowStyle Hidden proxy-watcher-only-tray.ps1`
  `-ProxyWatcherScript <run-proxy-watcher.ps1> -ProxyMapping <xlsx> -ProxyPythonPath
  <venv python> -ProxyAdbPath <adb> -ProxyRuntime <runtime dir> -ProxyWorkers 80`
- tray → child `run-proxy-watcher.ps1` (sets `$env:PYTHONPATH = <gan-proxy>/scripts`,
  builds `gan_proxy_fleet.py watch --all --workers 80 --mapping ... --poll-interval 30`)
- → python `gan_proxy_fleet.py watch` (PID A) → child python `gan_proxy_fleet.py watch` (PID B).
  **Two matching python PIDs is NORMAL** (PID B is spawned at startup — exact origin
  never pinned down; both share the watch-singleton lock; do not kill B thinking it's a
  duplicate). Tray `Ensure-ProxyWatcher` timer re-spawns the watcher if it dies.
- `run-proxy-watcher.ps1` default `-Mapping` is the OLD path
  `D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx` — the tray task XML
  `-ProxyMapping` argument is what actually overrides it.

## Restart procedure (config/runtime change only, no gateway)

1. `schtasks /Query /TN GanProxyWatcherTray /XML` → save `task.before.xml` (evidence).
2. `schtasks /End /TN GanProxyWatcherTray` (kills tray + watcher tree; the singleton
   `watcher-singleton.lock` is released on process exit).
3. Poll until no process matches `proxy-watcher-only-tray|run-proxy-watcher|gan_proxy_fleet.*watch`.
4. `schtasks /Run /TN GanProxyWatcherTray` → tray starts, `Start-ProxyWatcher` spawns child.
5. Verify child REALLY alive (tray Running is NOT proof): process command line contains
   `gan_proxy_fleet.py watch`, newest `watcher-logs\proxy-watcher-*.stdout.log` prints the
   command with the correct `--mapping`, and machine-N `watch-events.jsonl` gains
   `WATCH_WORKER_STARTED → WATCH_MONITORING` lines.

## Mapping path update via XML (schtasks quoting quirk)

- Edit the exported XML: replace the old `-ProxyMapping` value, write `task.updated.xml`.
- `schtasks /Create /TN GanProxyWatcherTray /XML "<path>" /F` — in git-bash the XML path
  must be passed as an UNQUOTED argument to `cmd.exe /c` (use `cygpath -w` and no inner
  quotes); a quoted path yields `ERROR: The filename, directory name, or volume label
  syntax is incorrect.` (first attempt with quotes failed; unquoted succeeded).
- Verify AFTER: re-export XML, assert new path present, old path absent, and the tray
  argv tokens (`proxy-watcher-only-tray.ps1`, `-ProxyPythonPath`, `-ProxyAdbPath`,
  `-ProxyRuntime`, `-ProxyWorkers`) unchanged.

## Device-lock semantics observed (core 0.4.44, protocol v2)

- Per-event transient locks: watcher holds `machine_<N>.lock.json` + `serial_<S>.lock.json`
  ONLY while processing a startup/reconnect event, then `finish(succeeded=True)` deletes
  both. No lock files = free target between events.
- Retained `handoff` locks (owner_active=False, `handoff_at` present) with a DEAD owner
  PID are reclaimable by watcher event lock via core `_takeover_payload` (FULL_SCOPE).
  Watcher startup event auto-reclaims a dead Tiktok_Reg handoff lock this way — no manual
  deletion. Evidence trail: `WATCH_EVENT_LOCK_ACQUIRED` in watch-events.jsonl.
- Live owner (running/recovery + PID alive) is NEVER overwritten; watcher retries up to
  `--lock-wait-timeout` then leaves the event.

## Soft-reboot auto-assign test (control script pattern)

Goal: reboot one machine and prove the watcher auto-assigns proxy afterwards, WITHOUT
racing it. Sequence that works:

1. `load_targets(mapping)` → exactly one Target for the machine; assert serial SHA-256
   prefix (never print the serial); keep the proxy value out of all output.
2. Acquire `DeviceLock(serial, machine, project='gan-proxy/scripts/gan_proxy_fleet.py',
   status='running', bypass_proxy_readiness=True).acquire()` (bypass avoids the 180s
   readiness wait).
3. Snapshot the machine's `watch-events.jsonl` size (events append to the SAME run dir
   `runtime/<run_id>/machine-N/watch-events.jsonl`).
4. `AdbClient(adb_path, serial).run(["reboot"], timeout=15, check=False)` — use
   `reboot.ok`/`reboot.exit_code` (AdbResult has NO `returncode`).
5. Release the lock in `finally` (`lock.finish(succeeded=True)`) so the watcher owns the
   reconnect event. Holding the lock through the reboot BLOCKS the watcher's event lock
   acquisition → no auto-assign. (Contrast: the repo's `run`-mode `reboot_target_once`
   holds its batch reservation and waits with `live_vpn_verifier`.)
6. Poll read-only until: `get-state` = device, `getprop sys.boot_completed` = 1, and the
   events file shows `WATCH_EVENT_DETECTED → WATCH_EVENT_LOCK_ACQUIRED →
   WATCH_CORE_READINESS_PASS → WATCH_PROXY_APPLICATION_SUCCESS →
   WATCH_ROTATION_RESTORE_SUCCESS → WATCH_VERIFICATION_SUCCESS →
   WATCH_PROXY_READINESS_READY → WATCH_EVENT_VERIFIED_SUCCESS`. Absence of
   `WATCH_CORE_READINESS_FAILURE`/TypeError = signature fix confirmed.
7. Live ADB proof: `ip addr show tun0` shows `tun0: <POINTOPOINT,UP,...>` + `inet
   <ip>/30`, and `dumpsys connectivity` has `type: VPN ... state: CONNECTED/CONNECTED`.
8. Write sanitized evidence: `pre-reboot.json`, `watch-events-before.jsonl`,
   `final-report.json` (statuses + timestamps, no serial/proxy) under
   `D:\CodexRuntime\codex_gmail_debug-gan-proxy\evidence\<stamp>\`.

Failure handling: one evidence-based recovery per the existing handler only; no blind
retry, no parallel proxy assignment, no `pm clear`/factory reset.

## Mapping workbook lock vs. watcher health

A live watcher process can remain healthy enough to append telemetry while being unable
to reload the canonical mapping. Repeated target-specific
`WATCH_MAPPING_RELOAD_ERROR` with `PermissionError`, together with a direct read-open
failure on the exact mapping path, can mean the workbook is still open exclusively in
Excel—not a TikTok navigation defect, dead watcher, burned proxy, or VPN implementation
bug.

Diagnose without reading secrets/cells:

1. Confirm the Scheduled Task/tray/watcher process tree is alive, but do not count that as
   readiness.
2. Snapshot the target event-log byte offset and inspect only new status/error metadata.
3. Probe exact-file readability and ordinary filesystem metadata/ACL.
4. Enumerate Excel workbook metadata only (`FullName`, `Saved`) and require exactly one
   normalized path match before attributing ownership.
5. Never dump workbook cells, formulas, names, connections, shared strings, proxy values,
   or credentials into evidence.

If a recovery is authorized to close the workbook, the safe design is exact-workbook only,
`Saved is True`, `Close(SaveChanges=False)`, with Excel events/alerts temporarily disabled
and restored in `finally`; verify size/mtime invariance and OOXML package framing afterward.
This close sequence is an audit-derived safety requirement—do not claim it was executed or
live-proven unless the run manifest contains actual pre/post evidence.

## Bind watcher readiness to one process generation

`GanProxyWatcherTray=Running`, matching PIDs, or an ordered status list can still stitch
stale/concurrent evidence. For a restart/recovery proof:

- export/hash the exact task XML and snapshot the old process tree;
- after `/Run`, bind the new top-level runtime UUID directory to the new watcher root PID,
  process creation time, descendants, and telemetry file under that exact directory;
- parse only events from that bound generation and time epoch;
- require one integer event number with the strict progression through
  `WATCH_EVENT_VERIFIED_SUCCESS`, correlated to the exact in-memory machine+serial;
- require the final reason (`SUCCESS` or `RECOVERED_SUCCESS`) and reject any matching
  mapping/serial/failure/final-blocked status;
- redact serial/IP/proxy from persisted artifacts.

Also distinguish a generic protocol-v2 inactive `handoff` from the structured post-reboot
owner-pause ACK. The latter requires a consistent `maintenance_handoff` on both aliases
(`mode=POST_REBOOT_PROXY_RECOVERY`, `state=OWNER_PAUSED`, handoff/boot/owner identity).
If a recovery plan depends on that ACK, check these fields explicitly; status `handoff`
alone is insufficient.

## Incident note (2026-08-12)

- `TypeError: watch_device_reconnect() got an unexpected keyword argument
  'auto_enable_wifi'` = watcher venv on core 0.4.43 while gan_proxy_fleet.py (0.4.44-era
  code) calls `auto_enable_wifi=WATCH_AUTO_ENABLE_WIFI` → fixed by installing 0.4.44.
- First `pip install` attempt "succeeded" into the HERMES venv because of the exported
  `PYTHONPATH`; re-ran with `env -u PYTHONPATH` and verified `__file__` +
  `importlib.metadata.version` before restarting the watcher.
- Repo `git status` gained FOREIGN edits (gan-proxy-all.bat, scripts/*.py, AGENTS.md)
  from a concurrent session DURING the runtime window — attribute via pre-change
  `git status`/`git diff --name-only` snapshot saved to evidence at session start plus
  file mtimes, not by assumption.
