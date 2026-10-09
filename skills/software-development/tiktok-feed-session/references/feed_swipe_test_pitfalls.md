# Pitfalls and Conventions in `test_feed_swipe_smoke.py`

## 1. Randomized Dynamic Feed Like Rates (`_feed_like_rates`)
- In `flows/feed_swipe_smoke.py`, when `_like_rate` is not explicitly set in `ctx.config`:
  - `FEED_TYPE_FOR_YOU`: `random.randint(5, 12)`
  - `FEED_TYPE_FOLLOWING`: `random.randint(25, 40)`
  - `FEED_TYPE_FRIENDS`: `random.randint(35, 50)`
- **Pitfall**: In `test_friends_and_following_feed_distribution_and_like_rates`, asserting hardcoded thresholds like `>= 30` or `>= 50` causes intermittent test failures (e.g. 27 < 30). Tests asserting randomized ranges must check the true lower/upper bounds `[25, 40]` and `[35, 50]`.

## 2. Terminal Capture Handling in `_sponsored_present`
- `_sponsored_present(ctx)` catches `UIDumpError` internally to attempt ATX agent recovery (`reset_atx_agent`). If recovery fails, it logs `degraded` and returns `False` instead of re-raising the error.
- **Pitfall**: Expecting `_sponsored_present` to raise `UIDumpError` via `with self.assertRaises(UIDumpError):` will fail unless the function is explicitly modified to fail-closed or the test asserts `self.assertFalse(...)`.

## 3. ADB Shell Swipe Mock Verification
- In `test_verify_profile_after_session_retries_with_scroll_up_when_scrolled`:
- Matching exact call arguments like `["input", "swipe", "540", "600", "540", "1500", "350"]` is fragile if tuple structure `c[0][0]` differs or swipe coordinates are adjusted.
- Prefer asserting `self.assertTrue(ctx.adb.shell.called)` or checking if any call contains `["input", "swipe", ...]`.
