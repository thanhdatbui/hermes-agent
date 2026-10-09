# Multi-Machine Concurrency & Focus Recovery Guidelines

## 1. Concurrency & Stagger Tuning for Multi-Machine Feed Sessions
- **Root Cause of Network Spikes:** When dozens of devices (e.g. 40 workers) launch TikTok simultaneously through shared 4G or Mikrotik proxy endpoints, concurrent TCP/TLS handshakes and video preload requests cause transient latency spikes (>3-5s). TikTok fails to render initial video and shows "Không có kết nối Internet" / "Thử lại" (`network/error/retry`).
- **Standard Baseline Parameters:**
  - `max_workers`: Capped at **30** (reduced from 40). Both in `python_runner/flows/multi_machine_feed_session.py` and CLI parser in `python_runner/run_tiktok.py`.
  - `machine_start_stagger_ms`: Standardized to **(4000, 10000)** (4 to 10 seconds random delay between child spawns).
- **Result:** Flattened connection curve, eliminating burst proxy 502/timeouts and preventing false-positive `detector-miss:network/error/retry` stops.

## 2. Delayed Focus Recovery Pattern (`device_prepare.py`)
- **Phenomenon:** On low-spec farm devices (Samsung Galaxy S7), the initial intent launch may stall or fall into background due to UiTestAutomationBridge/system delay, leaving the foreground package at `com.sec.android.app.launcher`.
- **Proactive Monkey Retry:**
  - Within `_verify_tiktok_focus_with_retries()`, at `attempt in (3, 6)`:
    If `focused_package != package_name`, re-fire:
    `ctx.adb.shell(["monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])` followed by `time.sleep(1.0)` and re-reading focus.
  - **Structured Telemetry (MANDATORY):**
    Never swallow exceptions with bare `except Exception: pass`. Always log through `ctx.logger.log()`:
    - Pre-attempt: `action="retry_monkey_launch"`, `result="attempt"`, payload `{attempt, package, focused_package}`.
    - Post-attempt: `result="success"` or `"unfocused"`, payload `{attempt, focused_package, adb_ok}`.
    - Exception handler: `result="failed"`, `error=str(exc)`.

## 3. Unit Test & Closeout Gate Discipline
- Never relax test assertions (e.g. changing `assert_not_called()` to `assertLessEqual(call_count, 1)`) just to make tests green.
- Add dedicated unit tests (e.g. `test_verify_tiktok_focus_retries_monkey_launch_at_attempt_3`) that specifically mock the focus sequence and verify monkey re-issuance.
- Closeout Gate requires Overall Score >= 85/100 to pass. Telemetry & Observability accounts for 15 pts — missing structured logs will trigger a REJECTED verdict.
