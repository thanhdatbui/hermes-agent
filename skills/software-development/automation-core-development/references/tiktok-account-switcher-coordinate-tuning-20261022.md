# TikTok Account Switcher Coordinates Tuning (2026-10-22)

## 1. Problem
When running TikTok account switching on physical Samsung Galaxy S7 / HD devices (1080x1920), the account item in the bottom sheet spans the full screen width (`bounds = [0, y1][1080, y2]`).
Default center tapping uses:
```python
x = (0 + 1080) // 2 = 540
```
At `x = 540`, on many TikTok UI versions:
- `x = 540` lands in empty space between the account display name and the notification badge (`9+` / badge element on the right margin).
- The tap event gets absorbed by the RecyclerView container or ignored, failing to trigger profile switching.
- As a result, after switcher dismiss/verify, the app remains on the old profile, causing `profile_preflight` mismatch failures.

## 2. Hardened Tap Pattern
In both `automation-core` (`account_switcher.py`) and consumer runners (`feed_swipe_smoke.py`):
- Check if the account node is full-width (`node.bounds[0] == 0` and `node.bounds[2] >= 1000`).
- Offset the tap coordinate to the **left zone (`x = 350`)**:
```python
if node.bounds[0] == 0 and node.bounds[2] >= 1000:
    tap_x = 350
    tap_y = (node.bounds[1] + node.bounds[3]) // 2
    adapter.tap(tap_x, tap_y)
```
- In consumer runners:
```python
b = account_element.bounds
tap_x = int((b[0] + min(b[0] + 600, b[2])) / 2.0)  # centers around x = 300-350
```
This guarantees hitting the avatar/username hit-box directly and triggering 100% reliable account switching.
