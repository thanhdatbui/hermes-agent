# TikTok Feed Session Test Suite Pitfalls & Verification

Khi chạy và verify test suite cho repo `tiktok-luot nuoi acc`:
`pytest python_runner/tests/test_feed_swipe_smoke.py python_runner/tests/test_user_placeholder_switcher.py --tb=short -q`

### 1. Calibrated Default Like Rates
Khi cập nhật tỷ lệ like mặc định `DEFAULT_FEED_LIKE_RATES` trong `python_runner/flows/feed_swipe_smoke.py`:
- Cần cập nhật đồng bộ các unit test trong `FastSwipeDeepInspectTests`:
  - `test_friends_and_following_feed_distribution_and_like_rates`
  - Chú ý: khi `FEED_TYPE_FRIENDS` được chỉnh thành 45% (hoặc `FEED_TYPE_FOLLOWING` thành 35%), assertion `self.assertEqual(DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FRIENDS], ...)` phải khớp với hằng số mới.

### 2. Natural Swipe Duration Assertions
- `_perform_feed_swipe` áp dụng jitter/drift tự nhiên mô phỏng hành vi vuốt của người thật.
- Giá trị `duration_ms` sinh ra có thể dao động dưới 400ms (ví dụ 250 - 350ms).
- Trong `test_feed_swipe_flow_does_not_call_social_actions`, assertion khoảng thời gian vuốt cần phản ánh đúng dải jitter hợp lệ (ví dụ `250 <= duration_ms <= 850`) thay vì cận dưới quá hẹp `400ms`.

### 3. ADB Shell Timeout Mock Matching
- Trong flow `verify_profile_after_session_retries_with_scroll_up_when_scrolled`, lệnh swipe scroll up gọi `ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"], timeout=ctx.timeout("adb_seconds", 15))`.
- Trong test mock, nếu `ctx.timeout` trả về giá trị khác `15` hoặc đối tượng mock của context không cấu hình trả về 15 mặc định, `assert_any_call` với `timeout=15` sẽ báo fail do mismatch timeout argument.

### 4. Terminal UI Dump Exception vs FlowResult Fail-Closed
- `test_sponsored_present_terminal_capture_error_fails_closed`: Kiểm tra xem flow có fail-closed an toàn khi gặp lỗi dump UI ở bước sponsored check. Cần lưu ý flow có thể nuốt exception và trả về `FlowResult(status=ExitStatus.FAILED)` thay vì ném ra `UIDumpError` trực tiếp ra ngoài test harness.
