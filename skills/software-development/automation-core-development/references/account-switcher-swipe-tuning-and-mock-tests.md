# TikTok Account Switcher Swipe Tuning & Mock Test Invariants

## Context & Viewport Characteristics
On Android test devices (specifically Samsung S7 / Galaxy farm devices at 1080x1920 resolution):
- The TikTok account switcher bottom sheet list generally populates between Y ≈ 1000 and Y ≈ 1800.
- When an account is not visible in the current viewport (`ACCOUNT_MISSING` in `find_exact_account`), the switcher scrolls down by swiping up:
  - `start_x, start_y = width // 2, int(height * 0.80)` (e.g. 540, 1536)
  - `end_x, end_y = width // 2, int(height * 0.50)` (e.g. 540, 960)
  - `duration_ms = 450` (slower, more stable swipe to prevent inertial overshoot on legacy Samsung touch controllers)
  - UI animation settle delay: `time.sleep(max(1.0, settle * 2))` before redumping UI XML.
  - Logging standard: Use module logger `logger = logging.getLogger(__name__)` with structured prefix `[ACCOUNT_SWITCHER]` for scroll attempts, missing account notices, and post-scroll account discovery.

## Test Assertion Synchronization Pitfall
In `automation-core/tests/test_account_switcher_preconfirmed.py`:
The unit test `test_select_exact_account_scrolls_when_missing()` uses `MockScrollAdapter` and asserts exact swipe coordinates:
```python
assert len(adapter.swipes) == 1
assert adapter.swipes[0] == (540, int(1920 * 0.80), 540, int(1920 * 0.50), 450)
```
Whenever swipe parameters in `select_exact_account()` are modified:
1. Ensure the mock adapter in `test_account_switcher_preconfirmed.py` receives the updated tuple expectation.
2. Verify immediately with:
   `PYTHONPATH=src pytest tests/test_account_switcher_preconfirmed.py`

## Profile Header Open Flow: Scroll-First Sticky Header Pattern (User Canonical Design)
On modern TikTok builds (v46.x+), opening the Account Switcher from the Personal Profile (`Hồ sơ`) tab requires strict sequencing:
1. **Never tap username/display-name in the body of the profile before scrolling**:
   Tapping body fields triggers bio editing, input method/keyboard popups, or profile picture dialogs, dirtying UI state.
2. **Scroll-first to anchor sticky header**:
   Perform a gentle upward swipe (`swipe 540 1000 540 700 250ms`, ~300px) so the account ID scrolls up and pins to the sticky header bar (`pmi` / `pmf` / `pcs` / `pq2` / `r2b`).
3. **Tap directly on the pinned ID at top-center**:
   Tap coordinates: `x ≈ sw // 2` (e.g. 511-540 on 1080p), `y ≈ 150` (bounds `[368, 132][654, 179]`).
   This pops open the `Chuyển đổi tài khoản` bottom sheet.
4. **Samsung Pay Edge Conflict Safety**:
   On Samsung Galaxy S7 (and devices with Samsung Pay Quick Pay bar at `[300, 1893][780, 1920]`), never initiate swipes with `y >= 1600` or below `1350`. Safe vertical swipe range for settings/switcher: `y ∈ [450, 1350]`.
5. **Anti-pattern**: Never invent a "log out" flow as a substitute for opening the switcher; follow the scroll-first sticky anchor sequence.
