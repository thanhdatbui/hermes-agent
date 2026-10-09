# Natural Follow Telemetry & Gating Contract

## 1. Bối Cảnh
Trong luồng nuôi tương tác TikTok (`feed_swipe_smoke.py`), hàm `_maybe_follow_video` chịu trách nhiệm quyết định và thực hiện follow ngẫu nhiên trên feed theo tỷ lệ cấu hình (`follow_rate_percent`).

## 2. Các Quy Tắc Gating & Telemetry
1. **Organic Rest Day & Video Count Gating**:
   - Tài khoản trong ngày nghỉ (`_is_organic_rest=True` hoặc `rest_day_no_follow`): Bỏ qua follow, log `action="follow_video"`, `result="skipped"`, `error="account is in organic rest day (0 follow)"`.
   - Tài khoản có dưới 10 video (`_video_count < 10`): Bỏ qua follow, log `action="follow_video"`, `result="skipped"`, `error="account has under 10 videos (natural follow disabled)"`.
2. **Tránh Silent Early-Return Trước Telemetry**:
   - **Pitfall**: Đặt `if int(follow_rate_percent) <= 0: return False` ở đầu hàm sẽ làm cho các trường hợp cấu hình follow rate = 0 (hoặc test cases kiểm thử roll skip) bị thoát sớm mà không ghi nhận structured log.
   - **Chuẩn hóa**: Tất cả các điều kiện loại trừ / skip follow do tỷ lệ hoặc gating phải ghi nhận telemetry log structured đầy đủ trước khi `return False`:
     ```python
     if random.randint(1, 100) > int(follow_rate_percent):
         ctx.logger.log(
             device_id=ctx.device_id,
             account=ctx.account,
             step=f"{after_attempt.get('step', 'swipe_after')}/follow",
             action="follow_video",
             result="skipped",
             error="roll skipped by follow rate percent",
             extra={"follow_rate_percent": follow_rate_percent},
         )
         return False
     ```
3. **Unit Test Setup cho `_maybe_follow_video`**:
   - Khi mock đối tượng UI XML trong test case kiểm tra follow thành công (`eligible`):
     - Node follow cần có `clickable="true"` và tọa độ `bounds` sao cho `center[1] >= 350` (tránh bị lọc bởi vùng header trên cùng).
     - Mock `ctx.timeout.return_value = 15` và `ctx.adb.shell.return_value = Mock(ok=True, stderr="")`.
