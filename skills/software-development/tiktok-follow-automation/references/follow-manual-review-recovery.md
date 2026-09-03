# Follow manual-review recovery: full-flow execution and transient row re-render

## Incident pattern
A feed-to-follow chain can record feed success while the downstream follow hook returns `MANUAL_REVIEW`. In the observed Mode 2 case, the result was `MANUAL_REVIEW: verify row sau tap không xác định (manual)`, with `followed_count=6` and `follow_failed=false`. This is a runner-verification error, not proof that Follow was released.

## Root cause
After tapping a follower-row Follow button, TikTok may briefly re-render the RecyclerView. A fresh UI dump can temporarily omit the exact target `txt_desc` row. Returning `manual` immediately from `_verify_row_after_tap()` creates a false blocker.

## Safe fix pattern
- Treat `current_row is None` as transient during the existing bounded `verify_reload_retries` loop.
- Sleep/recapture and retry; return `manual` only when the exact row is still absent after the retry budget.
- Preserve fail-closed behavior for ambiguous buttons, missing bounds, duplicate rows, identity mismatch, and unknown layouts.
- Do not reinterpret `MANUAL_REVIEW`, non-zero exit, or malformed output as `FOLLOW_FAILED`; only explicit post-tap evidence that the action returned to Follow/Follow lại may set release state.

## Regression fixture
Use a deterministic sequence that exercises the real call chain:
1. follower list with target row `Follow lại`;
2. transient follower list without the target row;
3. follower list with target row `Đã follow`;
4. a second followed-list dump consumed by Path B before opening the profile;
5. exact target profile with followed action;
6. restored follower list.

Assert `follow_one_follower()` returns `("followed", "")`. Keep separate tests proving missing/unknown button remains manual and profile identity/path-B failures remain manual.

## Full-flow acceptance
After a live fix, execute the canonical entrypoint for the exact machine/row and wait for the complete designed chain. Feed success is intermediate only when follow/upload hooks are part of the path. Read the final wrapper result, per-stage artifacts, hook result, explicit release flag, and lock state. If a child hook is running, inspect process/log/artifact activity and honor its configured timeout before cleanup; do not stop immediately at feed success.
