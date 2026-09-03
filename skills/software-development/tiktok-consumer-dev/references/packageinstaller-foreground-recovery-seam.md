# PackageInstaller foreground → typed deny handler (Task 5/6/7 seam)

Durable recipe for the `prepare_tiktok_app_for_automation` focus-failure route
that recovers a foreground Android PackageInstaller permission dialog via the
existing typed `dismiss_packageinstaller_dialog` handler instead of declaring
`focus failed`. Verified 2026-08-22 in the `tiktok-luot nuoi acc-implementation`
worktree (consumer repo) over the automation-core startup contract.

## Seam shape

Add `_maybe_recover_packageinstaller_focus(ctx, *, artifact_prefix,
focused_package, focused_activity) -> FlowResult | None` in
`python_runner/flows/device_prepare.py`. Wire it into
`prepare_tiktok_app_for_automation` **BEFORE** the `if not core_result.ok:` focus-
failure `return FlowResult(FAIL, ...)`. If it returns non-None, return that
(result is SUCCESS only on verified recovery); otherwise fall through to the
original FAIL.

Inside the helper, the four independently-observable sub-actions (each
telemetried, each mockable) are:

1. **Initial capture** — `capture_ui_xml(ctx.adb, timeout=...)` (raw capture,
   a DIFFERENT seam from the post-action recapture below) → if `xml` empty,
   fail-closed `return None` (no safe deny target). Save via
   `ctx.artifacts.save_text(...)`; screenshot via `ctx.adb.exec_out([...])`
   best-effort.
2. **Typed handler** — `dismiss_packageinstaller_dialog(ctx, before_attempt={
   "detected_screen": PACKAGEINSTALLER_DIALOG_SCREEN, "xml_path": ...,
   "screenshot_path": ..., "focused_package": ..., "focused_activity": ...},
   artifact_prefix=..., max_attempts=1)`. Require `dismiss.dismissed and
   dismiss.after_attempt is not None` else fail-closed.
3. **Recapture** — `capture_required_ui(ctx.adb, timeout=..., retries=1,
   recovery_package=...)`, wrapped in `try/except Exception: return None`
   (fail-closed; no success/resume/Home/reset when post-action UI unavailable).
4. **Focus recheck** — `get_focused_activity(ctx)`, wrapped in
   `try/except Exception: return None`. If `after_package == tiktok_package`
   return SUCCESS with `packageinstaller_recovered=True`; else fail-closed.

Imports needed in device_prepare.py:
`from core.benign_popup import PACKAGEINSTALLER_DIALOG_SCREEN`,
`from flows.benign_popup import dismiss_packageinstaller_dialog`,
`from automation_core.ui import ... capture_ui_xml`.

`_PACKAGEINSTALLER_FOREGROUND_PACKAGES = frozenset({
"com.google.android.packageinstaller", "com.android.packageinstaller"})`.

## TDD mock-harness pitfalls (cost real cycles)

- **Core retries focus up to `PREPARE_FOCUS_MAX_ATTEMPTS` (10).** To exercise
  the route, make the focus-reader return the PackageInstaller package for the
  FIRST N calls (N = `PREPARE_FOCUS_MAX_ATTEMPTS`) so `core_prepare_app_for_
  automation` concludes focus-failure; then return the post-deny package (e.g.
  TikTok) on the N+1-th call (the helper's post-recapture recheck). A global
  `return_value=PackageInstaller` makes core never fail, so the route is never
  hit and the handler mock shows `call_count == 0`.
- **Mock signature parity.** `capture_required_ui` is called positionally
  (`capture_required_ui(ctx.adb, timeout=..., ...)`). A test mock
  `lambda **k: ...` rejects the positional `adb` arg and raises *inside* the
  helper's `try` → silently swallowed → `return None` (looks like a logic bug,
  is actually a test-seam bug). Use `lambda adb, **k: ...`.
- **`PopupDismissResult` is a dataclass** with positional order
  `(dismissed, reason, before_attempt, after_attempt=None, ...)`. Construct as
  `PopupDismissResult(True, "r", {}, after_attempt={...})`.
- **`ctx.timeout(key, default)` accepts unknown keys** (returns `default`), so
  `ctx.timeout("ui_capture_seconds", 60)` is safe — but it still runs inside the
  recapture `try`, so a raised recapture fails closed (that is correct behavior;
  assert `recapture_mock.assert_called_once()` even when it raised, then
  `assertNotIn("packageinstaller_recovered", result.details)`).

## Test class layout (4+4+4 RED→GREEN classes in test_device_prepare.py)

- `PackageInstallerRecoveryTests` — route wiring: handler called once, recapture
  called once on success; fail-closed (no success/resume/Home/reset) when
  handler false / popup persists / recapture unavailable. Drive via
  `prepare_tiktok_app_for_automation` directly with the focus-reader sequence
  above.
- `PackageInstallerSuccessSemanticsTests` (Task 6) — success must attach to
  popup/package/focus proof, never a changed screenshot: image bytes "differ"
  but `after_attempt.detected_screen == "packageinstaller_dialog"` AND
  PackageInstaller still foreground → NOT success; handler false → not success;
  handler true + clean recapture + TikTok foreground → eligible; handler called
  but no recapture → not success (don't conflate "press happened" with
  "popup closed").
- `PackageInstallerBoundedRetryTests` (Task 7) — unsuccessful paths must NOT
  perform invalid retry / success report / resume / Home / reset; verified
  success path is bounded. `_execute_hard_stop` lives in `ai_recovery.agent`,
  NOT in `flows.device_prepare` — don't `patch("flows.device_prepare._execute_
  hard_stop")` (AttributeError); assert the FAIL result preserves the original
  `stop_reason` and no `packageinstaller_recovered` instead.

## RED evidence protocol

Disable the wiring call (comment the `_maybe_recover_packageinstaller_focus(...)`
block, keep `return FlowResult(FAIL, ...)`) and re-run the 4+4+4 suite → all
must FAIL at `handler_mock.assert_called_once()` (handler never called). Restore
wiring → all GREEN. A test that passes on baseline is NOT valid RED.

## Offline isolation

Run from `python_runner/` with the repo interpreter (avoid Hermes-venv PIL
poison): `env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe"
-m pytest python_runner/tests/test_device_prepare.py::PackageInstallerRecoveryTests
-q`. Core symbols resolve via `PYTHONPATH=D:/Taadaa/automation-core-implementation/src`.
Never `pip install -e` core into the runner env.
