# Natural Follow Gate & Patch Contract (tiktok-luot nuoi acc)

## Bối Cảnh & Mục Tiêu
Chặn hành vi follow tự nhiên trong quá trình nuôi nick (`feed_swipe_smoke.py` và `multi_machine_feed_session.py`) khi:
1. Nick đang bị phạt nhả follow (Follow Cooldown / Imprisoned).
2. Nick rơi vào ngày dưỡng sinh (`_is_organic_rest_day`).
3. Nick chưa đạt ngưỡng an toàn (dưới 10 video đã đăng).

## Quy Tắc Triển Khai (Patch Contract)

### 1. Child Config Mapping (`multi_machine_feed_session.py`)
Tại khối khởi tạo `child_config` trước khi chạy `feed_session_smoke`:
```python
is_organic = _is_account_organic_rest_day(account.machine, account.account_row_index)
child_config["_is_organic_rest"] = is_organic
video_count = getattr(account, "video_count", None)
if video_count is None:
    video_count = getattr(account, "video_posted", None)
try:
    video_count = int(video_count) if video_count not in (None, "", "None") else 0
except (ValueError, TypeError):
    video_count = 0
child_config["_video_count"] = video_count

if is_organic or video_count < 10 or os.environ.get("TAADAA_REST_DAY_NO_FOLLOW") == "1":
    child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}
```

### 2. Follow Execution Gates (`feed_swipe_smoke.py`)
Trong hàm `_maybe_follow_video(ctx, after_attempt, follow_rate_percent)`:
1. **Kiểm tra trạng thái nhả follow:** `is_account_in_follow_cooldown(ctx)` -> skip và log `error="account is in follow cooldown (imprisoned)"`.
2. **Kiểm tra ngày dưỡng sinh:** `cfg.get("_is_organic_rest") or cfg.get("rest_day_no_follow")` -> skip và log `error="account is in organic rest day (0 follow)"`.
3. **Kiểm tra ngưỡng video:** `int(cfg.get("_video_count")) < 10` -> skip và log `error="account has under 10 videos (natural follow disabled)"`.
4. **Watch Time Dwell Gate:** Ngâm tối thiểu 8.0 - 12.0s trước khi tap follow, ghi nhận `watch_dwell_seconds` vào log extra.

### 3. Test Suites & Verification
Được bao phủ trong `python_runner/tests/test_feed_like_rates.py`:
- `test_maybe_follow_video_skipped_on_organic_rest`
- `test_maybe_follow_video_skipped_under_10_videos`
- `test_maybe_follow_video_watch_dwell_gate_telemetry`
