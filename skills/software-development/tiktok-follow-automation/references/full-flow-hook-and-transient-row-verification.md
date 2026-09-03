# Full-flow hook and transient row verification

## User correction
A feed run that invokes the designed Follow hook is not complete when the feed stage succeeds. Keep the parent runner alive until the hook returns a terminal result and records its outcome.

Report these separately:

- feed success + Follow `OK` = full chain passed;
- feed success + `MANUAL_REVIEW`/script error = feed passed, Follow blocker remains;
- feed success + timeout = Follow hook timeout, not feed failure.

Do not kill the parent merely because the feed artifact is already `success`. Respect the hook's configured timeout. If the hook exceeds its bound without producing its result artifact, classify the hook separately and preserve the feed evidence.

## Mode 2 transient RecyclerView race
Immediately after a Follow tap, TikTok may re-render the follower RecyclerView and omit the exact target row from one fresh UI dump. Treat `_exact_current_row(...) is None` as transient while attempts remain:

1. recapture the UI;
2. if the exact row is absent and retry budget remains, wait briefly and retry;
3. classify the row button only after the exact row is rebound;
4. after the bounded retry budget is exhausted, return `MANUAL_REVIEW` fail-closed.

Never treat a transient missing row as `FOLLOW_FAILED`, success, or skipped. Preserve the existing unknown-button and persistent-missing-row safeguards.

## Required regression shape
Use a fixture sequence that mirrors the real caller: pre-tap exact follower row; post-tap transient list without that row; later exact row with `Đã follow`; Path B profile with exact identity and followed action; restored follower list. Keep a negative fixture proving a persistently missing row remains manual and does not tap a guessed coordinate.

## Evidence checklist

- Read the exact follow result and parent hook log, not only the feed summary.
- Confirm the `row`/account identity in `follow_result.json`.
- Separate explicit `FOLLOW_FAILED` from `MANUAL_REVIEW` and subprocess errors.
- For live reruns, use the exact machine/row target and a fresh artifact root.
- Before closeout, run the regression suite, inspect the exact staged diff, obtain the independent review verdict, and commit/push only the intended scope.
