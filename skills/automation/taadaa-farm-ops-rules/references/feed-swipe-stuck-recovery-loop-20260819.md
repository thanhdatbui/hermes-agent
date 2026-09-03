# Quy Tắc Vuốt Retry 2 Lần Trên Vòng Lặp Feed Chính (Feed Swipe Stuck Recovery) — 19/08/2026

## 1. Bối Cảnh & Vấn Đề
- Trên TikTok, hầu hết các popup quảng cáo (Closeup, Pepsi), bottom-sheet TikTok Shop, dialog khảo sát, live room, hay các lớp phủ CTA xuất hiện trong lúc lướt feed đều có thể trôi qua tự nhiên chỉ bằng một thao tác vuốt lên (swipe).
- **Lỗi đã xảy ra:** Trước đây hàm cứu hộ `_swipe_recovery_on_stuck` (vuốt thử 2 lần) chỉ được gắn ở nhánh popup allowlist cũ. Trong vòng lặp chính của `feed_swipe_smoke.py`, khi video gặp popup lạ và gán nhãn `manual-needed:popup`, code lập tức gọi `finalize_feed_session_cleanup()` ngắt phiên và báo alert dừng máy mà quên mất bước vuốt thử 2 lần.

## 2. Quy Tắc Cốt Lõi (User chốt 19/08)
> "Bất kì chỗ nào không qua được, không nhận diện được, script không giải quyết được thì vuốt retry tối đa 2 lần để qua trước khi báo lỗi."

1. **Phạm vi an toàn:** Áp dụng cho MỌI màn hình lạ/kẹt trong vòng lặp feed, **NGOẠI TRỪ** các màn hình nhạy cảm cần can thiệp bảo mật:
   - `manual-needed:login`
   - `manual-needed:login-overlay`
   - `manual-needed:verification`
   - `manual-needed:captcha`
   - `manual-needed:security`
   - `manual-needed:manual_challenge`
2. **Cơ chế thực thi:**
   - Khi `after["status"] in {"failed", ExitStatus.MANUAL_NEEDED.value}` trong vòng lặp `for video_idx in range(...)`:
   - Kiểm tra `detected` không thuộc nhóm nhạy cảm -> Gọi `_swipe_recovery_on_stuck(ctx, row=after, step=...)`.
   - `_swipe_recovery_on_stuck` thực hiện tối đa 2 lần swipe lên `(540, 1600) -> (540, 400)` và capture kiểm tra lại màn hình.
   - Nếu màn hình sau swipe trở về trạng thái feed hợp lệ (`for-you`, `following`, `friends`, `profile`) -> Gán `SUCCESS`, reset cờ `ctx.config["_swipe_recovery_used"] = False`, và tiếp tục vòng lặp nuôi acc mượt mà.
   - Chỉ khi sau 2 lần swipe mà vẫn kẹt cứng thì mới gọi cleanup và gửi alert dừng phiên.
