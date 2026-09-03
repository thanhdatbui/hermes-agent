# Alert-claim dedup & sponsored-gate contract (multi-machine-feed-session)

Condensed knowledge bank from the 2026-08-25 review pass and closeout on
`python_runner/flows/multi_machine_feed_session.py` + `feed_swipe_smoke.py`
(allowlist: those two + their two test files). Read before touching
alert-claim, session-key, ATX recovery, or sponsored-gate code in this repo.

## 1. At-most-once alert claim (`_claim_machine_alert_once`)

Claim layout: `<claim_root>/alert-claims/<session_key>/machine_N.claimed` (with backward compatibility for legacy `.pending` and `.uncertain`).

### The Atomic Pre-Send In-Flight Pattern
- **Why `.pending` with TTL was rejected**: If a marker uses `.pending` with an expiration TTL (e.g. 2h), a crash or process kill during or immediately after external `send_alert()` leaves `.pending` on disk. After TTL expires, a relaunch would see `.pending` expired, delete it, and re-send the alert, violating the invariant of "at most one external alert per machine per logical session".
- **Approved Solution**:
  1. Atomic `os.open(claimed, O_CREAT | O_EXCL)` is performed **BEFORE** calling `send_alert()`, writing `status=in_flight`.
  2. If file already exists (`claimed.exists()`, or legacy `pending.exists()` / `uncertain.exists()`), abort immediately (`return False`).
  3. `send_alert()` is invoked.
  4. If `delivered is True`, update the file to `status=delivered` and return `True`.
  5. If `send_alert()` returns `False`, `None`, raises an exception, or process terminates, the `.claimed` file remains permanently on disk (fail-closed, no auto-retry).
- **Producer-result semantics**:
  - `automation_core.alerts.send_farm_machine_alert(...)` returns `True` ONLY on clean success. It returns `False` on test-environment short-circuit, missing token, or caught exceptions.
  - Therefore `False` is ambiguous (cannot distinguish not-sent from timeout-after-send). The pre-created `.claimed` file ensures zero duplicate sends across any subsequent relaunches.

## 2. Session-key identity rules (`_feed_session_alert_key`)

- **Explicit Key Validation**: Config `_feed_session_alert_key` must be validated as ONE safe path component: reject absolute paths, `/` and `\` separators, `..`, `.`, empty/whitespace, and any characters outside `[\w.-]+` to prevent path traversal outside claim root.
- **Fail-Closed on Non-Row / Stale Contexts**: Non-row relaunches without a trustworthy `_account_row_index` or `row-<n>-<time>` regex in `artifact_root.name` must return `None` (fail-closed, suppress alert claim), NOT fallback to a generic `${day}-default` namespace (which could bypass existing `${day}-row<n>` claims).
- **No Wall-Clock Windows**: Never derive logical identity from hard-coded time buckets (`_FEED_ALERT_SESSION_WINDOWS` HH:MM). Use stable `_account_row_index` or scheduler `block_id_for(day, block_index, machine, account_id)`.

## 3. Root-resolution pitfalls (`_alert_claim_root`)

- `getattr(ctx.artifacts, "root", ctx.artifacts.run_dir)` evaluates the DEFAULT argument eagerly — raises `AttributeError` when `root` exists but `run_dir` does not. Use separate `getattr` calls / safe artifact-root resolution. Test with a stub exposing only `root`.
- Canonical-root walk: ancestors scanned for names `{"live", ".ai-runs"}`, then `YYYY-MM-DD` dated dirs, then `YYYYMMDD-HHMMSS` → parent. Ambiguous filesystem root + explicit session key present ⇒ return `None`.

## 4. ATX Recovery Hierarchy: Low-Level Reset vs Terminal Fail-Closed

Understanding the 2-tier architecture (vital when diagnosing "ATX lỗi thì cứu hay dừng?"):
1. **Tier 1 (Low-Level Auto-Recovery)**:
   - Inside `capture_required_ui` / `reset_atx_agent`, when ATX agent or UiAutomator stub crashes/hangs, it automatically tries to restart UiAutomator via `POST http://127.0.0.1:7912/uiautomator` (no monkey, background stub startup).
   - If recovery succeeds, fresh XML is dumped, `VERIFIED_HEALTHY` is restored, and the feed session proceeds normally without crashing.
2. **Tier 2 (Terminal Fail-Closed Escalation)**:
   - `ATX_SESSION_UNAVAILABLE` is ONLY raised to outer flows when Tier 1 recovery has been attempted and completely failed (budget exhausted or stub unrecoverable).
   - When `ATX_SESSION_UNAVAILABLE` reaches `_feed_session_flow`, the flow **MUST fail-closed immediately** (stop session, preserve lock, keep screen untouched, report alert). It must NEVER swallow the exception or fall back to destructive shell commands (`monkey`, `uiautomator dump`).

## 5. Sponsored-gate & Regression Testing Patterns (test_feed_swipe_smoke.py)

- **Production Gate**: `if is_feed_session and not fast_swipe_focus_lost and _sponsored_present(ctx)`:
  - If fast swipe loses TikTok focus (`focused_package != expected_package`), `fast_swipe_focus_lost = True` is set.
  - Video immediately escalates to Deep Inspect, skipping `sponsored_check` BEFORE recovery runs.
  - `_recover_post_swipe_launcher_focus` recovers focus, allowing later videos to resume `sponsored_check`.
- **Ordering Test Pattern**:
  - Mock `_recover_post_swipe_launcher_focus` must return a recovered `dict(after)` with `focus_package="com.ss.android.ugc.trill"`, `status="success"` so subsequent assertions test real state transition.
  - Record sequence markers: `sponsored_check` -> `swipe_1_after` -> `swipe_2_after` -> `recovery_restored_2` -> `sponsored_check` -> `swipe_4_after`.
  - Assert `focus_lost_window` (between `swipe_1_after` and `recovery_restored_2`) contains NO `sponsored_check`.
- **Outer-Flow Fail-Closed Test Pattern**:
  - When testing `UIDumpError("ATX_SESSION_UNAVAILABLE")` on `_feed_session_flow`:
    - Patch `_capture_step` on `step == "swipe_1_after"` to raise `UIDumpError`.
    - Track actions (`_perform_feed_swipe`, recovery helpers, `ctx.adb.shell`).
    - Ignore benign pre-flow setup commands (e.g. `settings put system accelerometer_rotation 0` for portrait lock).
    - Assert `with self.assertRaises(UIDumpError): _feed_session_flow(...)`.
    - Assert exactly 1 swipe took place before failure, and NO subsequent swipes, recovery, or forbidden shell commands occurred.
