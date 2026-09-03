# Zero-Following runtime loading and retry

## Trigger

Use this checklist when a live machine still emits the old Mode 2 error such as `mở tab Đã follow fail ... (lần 2)` after a zero-Following fix.

## Root cause pattern

A first `open_ok=False` branch may classify an empty anchor, while a later retry branch still treats the second `open_ok=False` as a generic UI failure. That fallback can overwrite the business classification and stop the session with `MANUAL_REVIEW`. The fix must preserve zero-Following classification across both the first attempt and the retry attempt.

## Safe classification

- Accept zero-Following only with exact target identity in the profile header and a Following label/count proof in the upper header region.
- A bare `0`, a generic `Follow` button, an unrelated `@handle`, or a suggested-account card is not proof.
- If tab navigation fails, re-probe the current screen before escalating. If the exact anchor still shows verified zero Following, return to Feed and continue with the next anchor.
- If Feed cannot be re-proven, keep `MANUAL_REVIEW`; do not force navigation.
- Keep relationship-state verification bound to the anchor's own action node. Suggested-account `Follow` buttons must never be interpreted as the anchor being unfollowed.

## Runtime-loading verification

1. Inspect staged and unstaged diffs; concurrent workers can leave an older retry branch in the working tree even after earlier tests passed.
2. Confirm the production hook invokes the canonical runner with `python -m follow_runner.run_follow` and `cwd=D:\Taadaa\tiktok-follow`.
3. From the same interpreter, print `module.__file__` and `inspect.getsourcefile(run_mode2)` to prove the imported module path.
4. Expose a harmless result/details build marker such as `mode2_zero_following_fix=zero-following-skip-v2`, then verify it in the child `FOLLOW_RESULT`.
5. Separate three claims: source patched, runtime loaded, and live behavior verified. Old screenshots or old timestamps cannot prove the new source was active.
6. Restart/relaunch only the new runner invocation; an already-running Python process does not reload modified modules.

## Regression pattern

Use fixtures for: (a) explicit `0 Đang follow`, (b) count and label split across nearby nodes, (c) suggested accounts below the header containing `@` and `Follow`, (d) first open failure followed by retry failure with a zero-proof re-probe, and (e) a true generic identity/UI failure that remains `MANUAL_REVIEW`. Run the focused Mode 2 tests and then the full suite; do not treat a truncated or timed-out test run as a pass.
