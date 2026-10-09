# Profile Navigation Retry & TikTok GO Card Patterns

## 1. Focus Recovery Navigation Retry Invariant (`calibrate_screens.py`)
- **Problem**: When a bottom/top navigation bar tap hits SystemUI (recent apps/nav bar) or launcher, `recover_tiktok_focus_after_systemui_tap` brings TikTok back to the foreground via `KEYCODE_BACK` or `monkey`. If the function immediately returns `NavigationResult(True, ...)`, callers assume the target screen (e.g. Profile or Inbox) was opened, when in reality TikTok only regained focus at its previous state.
- **Rule**:
  1. Once foreground focus is recovered, do **not** return success immediately.
  2. Perform an explicit retry tap to the target coordinates:
     ```python
     retry_tap = ctx.adb.shell(["input", "tap", str(x), str(y)], timeout=ctx.timeout("adb_seconds", 15))
     time.sleep(1.2)
     post_focus = get_focused_activity(ctx)
     post_package = str(post_focus.get("package") or "")
     post_activity = post_focus.get("activity")
     recovered_focus = (post_package == expected_package)
     ```
  3. Ensure any unit tests mocking `get_focused_activity` sequence include the post-retry-tap check.

---

## 2. Profile Screen Verification Discipline (`feed_swipe_smoke.py`)
- **Problem**: In `_verify_profile_after_session`, executing a blind pull-down swipe (`input swipe 540 600 540 1500 350`) when `not profile_screen_confirmed` disrupts whatever non-profile screen TikTok is currently displaying (Feed, Inbox, Camera, etc.).
- **Rule**:
  1. **Strict Gate**: If `not profile_screen_confirmed`, running `input swipe 540 600 540 1500 350` is **strictly forbidden**.
  2. **Navigation Retry**: When `not profile_screen_confirmed`, retry `tap_navigation_target(ctx, CalibrationTarget("profile", ("Hồ sơ", "Profile"), "bottom", required=True), ...)` up to 2 times and re-capture XML.
  3. **Conditional Swipe**: Only execute `input swipe 540 600 540 1500 350` when `profile_screen_confirmed is True` but the username anchor remains hidden/scrolled off-screen.

---

## 3. TikTok GO Card Dismissal Registry (`benign_popup_registry.py`)
- **Pattern**:
  - **Handler name**: `tiktok_go_card`
  - **Detector (`_detect_tiktok_go_card`)**:
    - Triggers if XML or OCR contains `"TikTok GO"` OR (`"Khám phá hòn ngọc địa phương"` / `"Khám phá những xu hướng mới nhất từ các nhà sáng tạo gần bạn"`).
    - AND contains action button `"Không quan tâm"` or `"Khám phá"`.
  - **Dismisser (`_dismiss_tiktok_go_card`)**:
    - Primary: find and tap node with text/desc `"Không quan tâm"` / `"Not interested"`.
    - Fallback: if not found, swipe up lightly past the card: `ctx.adb.shell(["input", "swipe", "540", "1400", "540", "600", "300"])`.

---

## 4. Exploration Guardrail: Zero Recursive Tree Walking
- **Pitfall**: Running `os.walk`, `glob(recursive=True)`, `grep -rn`, or searching across `D:\Taadaa\tiktok-luot nuoi acc` or large worktrees will freeze and hit the 900-second terminal timeout, burning through model turns.
- **Rule**: Always use direct file paths (e.g. `python_runner/flows/calibrate_screens.py`) or inspect single known directories with `os.listdir`.

---

## 5. Unit Test Execution & Environment Isolation Pitfall
- **Pitfall**: When running unit tests via `python -m unittest` on Windows host:
  1. Default shell environment `PYTHONPATH` can be polluted with agent venv paths (e.g., `hermes-agent/venv/Lib/site-packages`), causing binary module incompatibilities (such as `ImportError: cannot import name '_imaging' from 'PIL'`).
  2. Running unittest from outside repo root causes `ModuleNotFoundError: No module named 'python_runner/tests/...'`.
- **Command & Isolation Rule**:
  Always `cd` to the repository root and explicitly specify the isolated `PYTHONPATH`:
  ```bash
  cd "D:/Taadaa/tiktok-luot nuoi acc" && PYTHONPATH="D:\Taadaa\automation-core\src;D:\Taadaa\tiktok-luot nuoi acc\python_runner" python -m unittest python_runner/tests/<test_name>.py
  ```
- **Turn Budget Execution Discipline**:
  When user specifies a strict turn budget (e.g. "hoàn thành dưới 5 tool calls"), do NOT consume turns on iterative exploration or probing. Directly batch write-and-execute in a single script/patch pass.
