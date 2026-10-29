# Order Lifecycle Execution Order & Timeout Budget Safeguards

## 1. Problem Context: The App-Sync Starvation Trap

In automated order lifecycle engines combining farm device inspection (Phase 1: In-App ADB / OCR) and carrier Web APIs (Phase 2: Zero ADB Web Tracking):
- When several orders are placed simultaneously (e.g. batch voucher orders on 5+ farm devices), all new orders enter `NEED_APP_SYNC` (`status="Đã đặt hàng"`, `tracking_code=null`).
- If the lifecycle loop executes Phase 1 sequentially across all pending orders before Phase 2:
  - Each phone navigation/OCR attempt takes 30–60s.
  - 5 orders require 150–300s, exceeding the cron runner wrapper's execution timeout (120s / 180s).
  - Unhandled `subprocess.TimeoutExpired` crashes the runner with exit code 1, generating false "provider timeout / cron failure" alerts.
  - Crucially, **Phase 2 and local delivery hub alerts are starved and never executed**. Actionable milestones (such as parcel arrival at the destination hub) get delayed or completely missed.

## 2. Hard Architectural Rules

### Rule 1: Phase 2 (Web Tracking) & Watchdogs Run First (Zero ADB Inversion)
Phase 2 operates purely via HTTP Web APIs / carrier tracking pages without touching any farm phone or ADB bus (< 2 seconds total).
Always place Phase 2 and destination-hub alert watchdogs (e.g. `watch_jt_delivery_*`) **at the top of the lifecycle loop**, before any in-app sync logic is evaluated.

```python
# 1. Phase 2: Instant Carrier Web Tracking (<2s, Zero ADB)
orders_fresh = load_orders()
for o in orders_fresh:
    if classify_order_phase(o) == "ACTIVE_WEB_TRACKING":
        res = track_web_order(o, dry_run=dry_run)
        results["web_track_results"].append(res)

# 2. Local Destination Hub Alert Watchdogs (Actionable Telegram Sirens)
try:
    from watch_jt_delivery_40 import main as run_watchdog_40
    run_watchdog_40()
except Exception as exc:
    logger.warning("Lỗi chạy watch_jt_delivery_40: %s", exc)

# 3. Phase 1: In-App Sync (Bounded to at most 1 order per cron tick)
max_app_syncs = 1
app_syncs = 0
for o in orders:
    if classify_order_phase(o) != "NEED_APP_SYNC":
        continue
    if app_syncs >= max_app_syncs:
        break
    app_syncs += 1
    ...
```

### Rule 2: Strictly Bound App Sync per Cron Tick (`max_app_syncs = 1`)
Never iterate through all `NEED_APP_SYNC` orders in a single background cron tick. Cap execution to `max_app_syncs = 1` (or at most 2 with strict 30s timeouts). Newly placed orders (less than 12–24h old) rarely have tracking codes immediately available anyway; staggering their inspection across 6h cron windows prevents farm device overheating and battery drain.

### Rule 3: Graceful Wrapper Subprocess Timeout (Silent Watchdog Pattern)
The cron runner wrapper (`cron_order_lifecycle.py`) must catch `subprocess.TimeoutExpired` cleanly, write a concise warning to `sys.stderr`, and exit 0. Under `no_agent: true`, non-zero exit sends noisy failure alerts to Telegram, violating the silent watchdog invariant.

```python
try:
    proc = subprocess.run(
        [sys.executable, str(TARGET_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(ORDERS_DIR),
    )
except subprocess.TimeoutExpired:
    sys.stderr.write("Timeout: order_lifecycle.py vượt quá 180s; bỏ qua chu kỳ watchdog này.\n")
    sys.exit(0)
```

### Rule 4: Orphan Device Lock Reaper with Unset Machine Fields
When `operator_device_lock` is invoked with `serial` but without an integer `machine` parameter, the resulting lock file (`serial_<serial>.lock.json`) contains `"machine": ""`. Reapers (such as `reap-dead-owner-locks.py`) must not skip these locks if the owner process is definitively dead (`owner_process_alive(d) is False`). Dead-owner locks must be reaped into quarantine immediately to prevent stale device-lock deadlocks on subsequent runs.
