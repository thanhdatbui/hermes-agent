# Follow Watchdog Error Classification & Diagnosis

## 1. Watchdog Follow Report Semantics

Watchdog (`feed_session_watchdog.py`) groups Follow results into 4 strict categories:
- **Success**: `status in {"OK", "SUCCESS"}` and `len(followed) > 0`.
- **Nhả follow**: Only `status == "FOLLOW_FAILED"` or `follow_failed is True`. (Real TikTok unfollow/rollback observed post-refresh).
- **Bỏ qua**: `status == "SKIPPED"` (e.g. `follow-released-daily-cooldown`, 0 video, warmup rows 3..6).
- **Lỗi script/xác minh**: Everything else (all `MANUAL_REVIEW`, timeouts, process errors, missing `follow_result.json`).

## 2. Common Causes of "Lỗi script/xác minh"

When a large batch of machines reports "Lỗi script/xác minh":

1. **Mode 1 Fallback Manual Review (`MANUAL_REVIEW: không thấy đúng một nút Follow trên exact profile`)**:
   - In hybrid mode (`both`), Mode 2 runs first on anchor following lists. When internal farm accounts in the anchor list are exhausted or already followed, the runner falls through to Mode 1 (Search direct UID from `taikhoan_run_safe.xlsx`) to fill the remaining session budget.
   - When Mode 1 lands on the profile of a searched target UID, `_classify_exact_profile_action()` requires finding exactly one action button matching `_ACTION_BUTTON_IDS` (`id/fds` / `id/ff8`). If the target profile has friend recommendations, multiple action buttons, or different layout elements, the classifier returns `"unknown"` and aborts with `MANUAL_REVIEW`.
   - **Crucial**: This is a fail-closed safety invariant to prevent blind coordinate tapping. It is NOT account penalty or follow release.

2. **Missing Follow Result File (`NO_FILE`)**:
   - Machine was held in device-lock from a previous crashed run or failed during the Feed session before reaching the follow hook.

3. **Mode 2 Row Verification Uncertainty (`MANUAL_REVIEW: verify row sau tap không xác định`)**:
   - In Mode 2's following list, row-level button classification could not unambiguously determine if the button transitioned to followed state.
