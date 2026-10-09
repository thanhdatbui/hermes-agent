# Quy Tắc Chặn Follow Tự Nhiên (Feed Session) & Pitfall Mock Testing

## 1. Mục Đích & Bối Cảnh
Tránh tình trạng tài khoản bị phạt, bị follow jail, hoặc bị hệ thống TikTok âm thầm revert follow (nhả follow) do:
- Bấm follow trong ngày nghỉ dưỡng sinh (Organic Rest Day).
- Tài khoản mới chưa đạt độ uy tín (đăng dưới 10 video).
- Tương tác quá nhanh không ngâm đủ watch dwell time.

## 2. Các Cổng Kiểm Soát (Gating Logic) Trong Feed Session

### A. Truyền Cờ Phân Luồng (`multi_machine_feed_session.py`)
Khi khởi tạo child process (`_run_child`):
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

# Ép follow rate về 0 khi đang dưỡng sinh, dưới 10 video hoặc biến môi trường yêu cầu
if is_organic or video_count < 10 or os.environ.get("TAADAA_REST_DAY_NO_FOLLOW") == "1":
    child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}
```

### B. Kiểm Soát Tại Điểm Thực Thi (`_maybe_follow_video` trong `feed_swipe_smoke.py`)
```python
# 1. Kiểm tra ngày nghỉ dưỡng sinh
cfg = getattr(ctx, "config", {}) or {}
if not isinstance(cfg, dict):
    cfg = {}

if cfg.get("_is_organic_rest") or cfg.get("rest_day_no_follow"):
    ctx.logger.log(
        device_id=ctx.device_id,
        account=ctx.account,
        step=f"{after_attempt.get('step', 'swipe_after')}/follow",
        action="follow_video",
        result="skipped",
        error="account is in organic rest day (0 follow)",
        extra={"follow_rate_percent": follow_rate_percent},
    )
    return False

# 2. Kiểm tra số lượng video đã đăng
video_count = cfg.get("_video_count")
if video_count is not None:
    try:
        if int(video_count) < 10:
            ctx.logger.log(
                device_id=ctx.device_id,
                account=ctx.account,
                step=f"{after_attempt.get('step', 'swipe_after')}/follow",
                action="follow_video",
                result="skipped",
                error="account has under 10 videos (natural follow disabled)",
                extra={"follow_rate_percent": follow_rate_percent, "video_count": int(video_count)},
            )
            return False
    except (ValueError, TypeError):
        pass

# 3. Watch Dwell Gate (ngâm video 8-12s trước khi tap follow)
watch_dwell_s = round(random.uniform(8.0, 12.0), 2)
time.sleep(watch_dwell_s)
```

## 3. Pitfall Lập Trình: Mock Trap Trong Pytest / Unittest

### Vấn Đề
Khi kiểm thử unit test với `ctx = Mock()`:
- `getattr(ctx, "config", {})` trả về một Mock instance thay vì `{}` nếu `ctx.config` chưa được gán rõ ràng.
- `cfg.get("_is_organic_rest")` trên Mock instance sẽ trả về một Mock con (`<Mock name='mock.config.get()'>`).
- Trong Python: `bool(Mock()) == True`. Do đó, điều kiện `if cfg.get("_is_organic_rest"):` sẽ luôn đánh giá thành `True`, làm ngắt đột ngột mọi luồng thực thi trong các test case khác (gây false positive và fail assertion).

### Cách Khắc Phục Chuẩn
Luôn ép kiểu dictionary trước khi truy xuất:
```python
cfg = getattr(ctx, "config", {}) or {}
if not isinstance(cfg, dict):
    cfg = {}
```
Điều này đảm bảo khi test mock không truyền config dictionary, `cfg` sẽ là `{}` rỗng an toàn.
