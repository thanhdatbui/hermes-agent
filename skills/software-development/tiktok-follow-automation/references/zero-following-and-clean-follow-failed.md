# Zero-Following Anchors and Clean FOLLOW_FAILED Handling

## Scope

This reference records the reusable regression pattern from the Mode 2 follow runner. It is not a live-device procedure and must not be used to infer a target machine or serial.

## Root-cause pattern

A farm anchor can be valid and already followed while having zero accounts in Following. Tapping its Following statistic does not open a list; treating that as a navigation failure causes an unnecessary retry ladder and `MANUAL_REVIEW`. The correct classification is exhausted business input.

Use the fresh profile XML already captured for identity verification. Accept both:

- a combined counter/label such as `0 Đang follow`, `0 Đã follow`, or `0 Following`;
- a separate `0` counter positioned beside a Following label in the profile header.

The zero-count check must run before the Following tap and before any anchor-follow action. On a positive match, append a reason such as `anchor @<uid> có 0 Following (danh sách rỗng)`, return to a proven Feed surface, continue to the next anchor, and leave the follow budget unchanged. If Feed cannot be re-proven after the bounded recovery path, then and only then return `MANUAL_REVIEW`.

## Result-state contract

`FOLLOW_FAILED` means TikTok did not retain a requested follow. It is a clean business stop when app cleanup succeeds: stop the current session, persist the daily cooldown/failure date, close the app through the normal adapter, and do not alert the operator.

`CLEANUP_FAILED` is different: cleanup after `OK` or `FOLLOW_FAILED` is unavailable or raises. Preserve `follow_failed`, set `failed=True`, retain the technical reason, and allow the normal technical-alert path. Never silently swallow this failure.

`MANUAL_REVIEW`, configuration errors, and other technical failures remain fail-closed and alertable.

## Regression recipe

Focused tests should cover:

1. zero-count profile detection for combined and split counter formats;
2. zero-count anchor skipped without tapping Following, following the anchor, or consuming budget;
3. next anchor still runs and can use the unchanged budget;
4. successful `FOLLOW_FAILED` cleanup calls `close_all_recent_apps` and returns the clean-stop exit code;
5. missing/raising cleanup becomes `CLEANUP_FAILED` and fails closed;
6. technical failures still take the alert path.

Recommended offline verification:

```text
python -m pytest -q follow_runner/tests/test_mode2_follow_followers.py follow_runner/tests/test_mode2_following.py
python -m py_compile follow_runner/flows/mode2_follow_followers.py follow_runner/core/selectors.py follow_runner/tests/test_mode2_follow_followers.py follow_runner/tests/test_mode2_following.py
python -m pytest -q follow_runner/tests/test_case49_follow_failed_cleanup.py follow_runner/tests/test_cli.py
python -m py_compile follow_runner/run_follow.py follow_runner/tests/test_case49_follow_failed_cleanup.py follow_runner/tests/test_cli.py
 git diff --check
```

Keep the farm case catalog synchronized when this behavior changes. Do not use ADB taps, a live batch, or a guessed canary target as a substitute for the offline regression proof.