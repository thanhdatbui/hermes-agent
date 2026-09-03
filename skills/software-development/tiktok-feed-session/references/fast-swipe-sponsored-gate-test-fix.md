# Fast-swipe sponsored gate — regression test fix (2026-08-25)

Repo: D:\Taadaa\tiktok-luot nuoi acc · File touched: ONLY python_runner/tests/test_feed_swipe_smoke.py

## Production contract (verified, do not change)

Gate inside `_feed_session_flow` (flows/feed_swipe_smoke.py):

```python
if (
    is_feed_session
    and not fast_swipe_focus_lost
    and _sponsored_present(ctx)
):
```

- `fast_swipe_focus_lost` is set True when focus check after a FAST swipe sees a non-TikTok package; the row then falls through to the full Deep Inspect chain (swipe + `swipe_N_after` capture + launcher recovery ladder) WITHOUT evaluating the sponsored gate.
- The flag RESETS to False at the top of EVERY video iteration — so the gate is evaluated once per video that reaches Deep Inspect, including all videos after a recovered focus loss.

Per-video event order: [fast path: swipe -> focus check -> (fast row + continue) | deep path: ...] then Deep Inspect: build params -> SPONSORED GATE -> `_perform_feed_swipe` -> `swipe_N_after` capture.

## Failure mode seen

Test `FastSwipeDeepInspectTests::test_fast_focus_lost_skips_sponsored_check_before_recovery` patched `_sponsored_present(side_effect=AssertionError("..."))` for the WHOLE session and asserted `assert_not_called()`. With total_videos=4 (chu kỳ [2]: v1 D | v2 F→focus-lost→D | v3 F | v4 D-last) the legal sequence is:

```
sponsored_check(v1) -> swipe_1_after -> [focus-lost segment: NO gate] -> swipe_2_after -> sponsored_check(v4) -> swipe_4_after
```

The v4 gate call is correct production behavior, so the always-raising stub failed the test. Test bug, not prod bug.

## Fix pattern (ordered-event capture)

- One shared `events: list[str]`. Patched callback: `events.append("sponsored_check"); return False`. Pass the SAME list as `captures=` so the fake `_capture_step` appends step names onto the same timeline.
- Window assert: `focus_lost_window = events[events.index("swipe_1_after")+1 : events.index("swipe_2_after")]` must NOT contain `"sponsored_check"`.
- Sequence assert: filtered markers equal exactly `[sponsored_check, swipe_1_after, swipe_2_after, sponsored_check, swipe_4_after]`.
- Sibling test `test_sponsored_present_terminal_capture_error_fails_closed` (UIDumpError fail-closed) left untouched.

## Session discipline observed

- Baseline `git status --porcelain` captured BEFORE edits (4 dirty files); the two multi_machine_feed_session* dirty files stayed untouched; no reset/stash/commit/push.
- Verification: RED (focused test fails with the documented AssertionError reason) -> rewrite -> GREEN -> full file suite `python -m pytest python_runner/tests/test_feed_swipe_smoke.py -q` (53 passed) -> `py_compile` OK -> `git diff --check` OK -> report exact result + diff.
