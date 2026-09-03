# Account Update Prompt Dismiss & _row_from_attempt Contract (2026-08-24)

## Bối cảnh & Hiện tượng
Máy 54 (và các máy live gặp popup cập nhật bảo mật tài khoản "Tài khoản của bạn cần được cập nhật" / `account_update_prompt`) bị dừng phiên với lỗi:
`TypeError: _row_from_attempt() got an unexpected keyword argument 'artifact_prefix'`.

## Nguyên nhân gốc
Trong `python_runner/flows/feed_swipe_smoke.py`, hàm `_maybe_dismiss_account_update_prompt_row` khi construct row sau khi dismiss đã gọi:
```python
after_row = _row_from_attempt(
    step=after_step,
    action="observe",
    expected=after_expected,
    attempt=after_attempt,
    swipe_count=row.get("swipe_count", 0),
    require_feed=after_require_feed,
    artifact_prefix=artifact_prefix,  # LỖI: _row_from_attempt không chấp nhận tham số này
)
```
Đồng thời thiếu:
1. Tham số `expected_package=str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))`.
2. Chuyển đổi `.as_dict()` từ `FeedStep`.
3. Gán `after_row["attempts"] = [dismiss.after_attempt]` và đồng bộ metadata `detected`, `focus_package`, `focus_activity`, `artifact_path`.
4. Ghi partial result `_store_partial_result(...)` và ghi log `ctx.logger.log(..., result=after_row["status"])`.

## Chuẩn mực gọi `_row_from_attempt` trong Benign Popup Handlers
```python
after_row = _row_from_attempt(
    step=after_step,
    action="observe",
    expected=after_expected,
    swipe_count=int(row.get("swipe_count") or 0),
    attempt=dismiss.after_attempt,
    expected_package=str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill")),
    require_feed=after_require_feed,
).as_dict()

after_row["attempts"] = [dismiss.after_attempt]
after_row["popup_type"] = "account_update_prompt"
after_row["popup_dismiss_action"] = "dismiss_later_button"
after_row["popup_dismissed"] = True
after_row["popup_dismiss_reason"] = dismiss.reason
if dismiss.selector:
    after_row["popup_dismiss_selector"] = dismiss.selector

results.append(after_row)
_store_partial_result(
    ctx,
    results,
    max_swipes,
    mode_name=mode_name,
    summary_key=summary_key,
    status_key=status_key,
    watch_delay_min_seconds=watch_delay_min_seconds,
    watch_delay_max_seconds=watch_delay_max_seconds,
    watch_delay_samples=watch_delay_samples,
    min_swipe_duration_ms=min_swipe_duration_ms,
    max_swipe_duration_ms=max_swipe_duration_ms,
    swipe_jitter_px=swipe_jitter_px,
)
ctx.logger.log(
    device_id=ctx.device_id,
    account=ctx.account,
    step=f"{artifact_prefix}/{after_step}",
    action="observe",
    result=after_row["status"],
    artifact_path=after_row.get("artifact_path"),
    extra=after_row,
)
return after_row
```

## Regression Test
File: `python_runner/tests/test_feed_swipe_smoke_popups.py` -> `test_account_update_prompt_row_dismiss_and_row_construction`.
Kiểm tra dismiss popup thành công, row status là `success`, popup_type đúng và không quăng TypeError.
