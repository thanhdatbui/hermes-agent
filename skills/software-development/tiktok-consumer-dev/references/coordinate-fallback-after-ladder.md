# Coordinate-fallback tầng cuối after ladder exhaustion — Tiktok-video recipe

Implemented 2026-08-09 in `D:\Taadaa\Tiktok-video` per automation-core rule
`ui-coordinate-fallback-after-recovery-ladder-20260808` (contract §"Coordinate
fallback after UI recovery ladder exhaustion"). This is the CONSUMER-HANDLER-level
visual layer (not the `adapter.coordinate_fallback(action)` hook — that is a
different core contract; grep the core for `coordinate_fallback` before choosing).

## Ladder ordering that precedes it (current policy; do not re-order)

1. `_wait_for_feed`: `consecutive_dump_failures >= 2` + `not atx_recovered` +
   `adapter._adb` → `_recover_uiautomator(adb, timeout=10, attempts=[], label="wait_feed_atx_kill")`
   once per signature.
2. `_handle_open_tiktok`: exactly one force-stop + relaunch pass (`APP_RELAUNCH_MAX_ATTEMPTS = 1`).
3. `_maybe_soft_reboot_recovery()`: exactly one soft reboot, only when authorized/eligible; otherwise fail-closed.
4. Evidence-gated coordinate fallback after the ladder is exhausted; safe target only,
   one tap at most, mandatory recapture, then `FINAL_BLOCKED` on failure.

## Insertion point + flow

Insert AFTER `if self._maybe_soft_reboot_recovery(): return False`, BEFORE
`self.context.is_ui_unavailable = True`:

```python
if self.context.config.get("allow_device_reboot_recovery", True) is False:
    # reboot forbidden ⇒ coordinate fallback forbidden → straight MANUAL_REVIEW
    ...
else:
    if self._coordinate_fallback_after_ladder_exhausted(adapter, feed_indicators):
        self.context.is_ui_unavailable = False
        self.context.error = None
        return True
```

`_coordinate_fallback_after_ladder_exhausted(adapter, indicators) -> bool`:
1. `device_transport` required, else False.
2. Evidence screenshot via `_capture_coordinate_fallback_artifact()` (mirror
   `_capture_soft_reboot_artifact`; filename `coordinate-fallback-<state>-before.png`;
   run_dir = `reporter.run_dir` or `config["runtime_root"]`), None ⇒ FINAL_BLOCKED.
3. `self._visual_feed_surface_visible()` True ⇒ accept feed, log
   `"[OPEN_TIKTOK] Feed xác nhận bằng visual sau ladder cạn — coordinate fallback"`,
   write `checkpoint["coordinate_fallback"]` record, return True.
4. `_bottom_nav_home_point_scaled(adapter)`: parse `adb.shell(["wm","size"], timeout=5,
   check=False)` stdout, `re.search(r"Override size:\s*(\d+)x(\d+)")` FIRST, fall back
   to Physical, then bare digits; None ⇒ no tap. Home = `(width // 10, height - 40)`.
5. `_screenshot_shows_bottom_nav_strip(path)`: PIL crop (0, 0.93h)-(w, 0.995h); if
   dark fraction (`max(rgb) < 60`) > 0.85 ⇒ no clear target (màn đen signature) ⇒ no
   tap. This is the no-blind-tap evidence gate.
6. `transport.tap(x, y)` in try/except; then recapture `self._wait_for_feed(adapter,
   indicators, timeout=30)`. Fail ⇒ FINAL_BLOCKED, NEVER retry same coords. Log + record
   action/coords/recaptured in `checkpoint["coordinate_fallback"]` (precondition,
   expected_postcondition, screenshot, rule id).

## Regression tests (added to TestStateMachine in tests/test_tiktok_workflow.py)

- `test_handle_open_tiktok_accepts_visual_feed_after_recovery_ladder_exhausted`:
  dump_ui raises `AccountSwitcherError("uiautomator null root node")` forever;
  `machine._wait_for_feed = lambda *a, **k: False`; `_maybe_soft_reboot_recovery`→False;
  `_visual_feed_surface_visible`→True; fake transport `screenshot()` writes bytes;
  monkeypatch module `prepare_app_for_automation` → SimpleNamespace(ok=True, steps=());
  `StateContext(config={"runtime_root": tmp_path}, adapter, device_transport, dry_run=False)`;
  assert `_handle_open_tiktok() is True`.
- `test_handle_open_tiktok_coordinate_tap_scaled_by_wm_size_after_ladder_exhausted`:
  same setup + `_visual_feed_surface_visible`→False; fake `_adb.shell` returns
  `ok=True, stdout="Override size: 720x1280\nPhysical size: 1080x1920"`; transport
  `screenshot()` writes a REAL PIL image 720x1280 white + light-gray bottom strip +
  small dark icon (so the strip gate passes); recapture `_wait_for_feed`→False ⇒
  `_handle_open_tiktok() is False` and `transport.taps == [(72, 1240)]`.
- Escape care: in the test source the wm-size stdout escape is `"Override size:
  720x1280\nPhysical size: 1080x1920"` (literal backslash-n escape in the file).

## COMPAT entry (docs/tiktok-ui-compatibility.md)

Append to the existing COMPAT-OPEN-TIKTOK-002 numbered ladder list:

```
  4. Tầng cuối mới (coordinate fallback sau ladder cạn — rule core
     `ui-coordinate-fallback-after-recovery-ladder-20260808`): sau **đúng một** force-stop/relaunch + **đúng một soft-reboot authorized/eligible** (ATX kill đã chạy trước đó), nếu visual gate xác nhận feed thật (XML vẫn null) → chấp nhận feed; có screenshot evidence target rõ (dải bottom-nav không đen) → tap tọa độ bottom-nav home scaled theo `wm size` override → recapture `_wait_for_feed` ngắn (30s) verify; fail → FINAL_BLOCKED, không retry cùng tọa độ; cấm toàn bộ khi `allow_device_reboot_recovery=False`. **Mọi mô tả lịch sử về nhiều lần relaunch hoặc nhiều app-launch pass đều đã superseded và không runnable.**
```

Also extend the entry's "Regression tests" line with both new test names. Docs file is
pure CRLF — append via byte-exact replace, not the patch tool.

## EOL verification numbers (before → after)

- `state_machine.py`: 10728 → 10932 CRLF, 0 lone LF.
- `tests/test_tiktok_workflow.py`: 9016 → 9144 LF, 0 CRLF.
- `docs/tiktok-ui-compatibility.md`: 1128 → 1129 CRLF, 0 lone LF.
- `git diff --check` clean; `git diff --stat` shows exactly the 3 scoped files.

## Notes

- Pillow 14 deprecates `Image.getdata()` (use `get_flattened_data`), but existing
  code (`_visual_feed_surface_visible`, `_tap_visual_create_button`) uses
  `list(crop.getdata())` — keep the new helper consistent with the codebase; the
  DeprecationWarning is pre-existing noise, not a regression.
- Run full test file after the `-k` filter pass (317 passed here) to catch collateral
  breaks; use `PYTHONPATH="D:/Taadaa/Tiktok-video/scripts"` + the repo venv
  `/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe`, never the Hermes venv.
