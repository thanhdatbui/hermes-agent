# Pitfalls & Mock Requirements for `test_feed_swipe_smoke.py`

### 1. `_feed_like_rates` Range Assertions
* **Logic flow:** Rate ngẫu nhiên cho `FEED_TYPE_FOLLOWING` và `FEED_TYPE_FRIENDS` trong cấu hình mặc định:
  - `FEED_TYPE_FOLLOWING`: [25%, 40%] (hoặc phụ thuộc config override).
  - `FEED_TYPE_FRIENDS`: [35%, 50%].
* **Pitfall in Unit Tests:** Assert `assertGreaterEqual(like_rates[FEED_TYPE_FOLLOWING], 30)` hay `assertGreaterEqual(like_rates[FEED_TYPE_FRIENDS], 50)` sẽ bị fail nếu dải cấu hình chuẩn mở rộng xuống 25% và chặn trên ở 40% / 50%.
* **Fix:** Khớp assertions trong `test_friends_and_following_feed_distribution_and_like_rates` đúng với dải chặn thực tế cấu hình.

### 2. `_verify_profile_after_session` Scroll Up Retry
* **Logic flow:** Trước khi gọi lệnh ADB shell vuốt ngược màn hình lên để lộ username, hàm kiểm tra điều kiện `if not matched and profile_screen_confirmed:`.
* **Pitfall in Unit Tests:** Nếu fixture XML mock (`xml_scrolled`, `xml_scrolled_2`) chỉ chứa text mà thiếu indicator tab Profile được chọn (ví dụ `<node text="Hồ sơ" selected="true" bounds="..."/>` hoặc `<node text="Profile" selected="true" bounds="..."/>`), `_profile_screen_confirmed_from_xml` sẽ trả về `False`. Khi đó `profile_screen_confirmed` là `False`, script bỏ qua nhánh cuộn và không gọi ADB shell, dẫn đến fail assertion `ctx.adb.shell.called`.
* **Fix:** Luôn đảm bảo fixture XML mock cho màn hình profile bị cuộn chứa node tab `"Hồ sơ"` hoặc `"Profile"` có `selected="true"`.

### 3. `_sponsored_present` Terminal Capture Error Fails Closed
* **Logic flow:** `_sponsored_present(ctx)` gọi capture UI XML thông qua các cơ chế nội bộ (`ctx.adb.dump_ui_xml` / `_capture_xml_text` / `_capture_with_ui_source`).
* **Pitfall in Unit Tests:** Nếu test patch `_capture_xml_text` nhưng hàm `_sponsored_present` gọi hàm capture cấp thấp khác (như `dump_ui_xml`), hoặc `_sponsored_present` bắt và nuốt lỗi thành fallback `False`, khối `with self.assertRaises(...)` sẽ fail vì không nhận được ngoại lệ.
* **Fix:** Đảm bảo patch đúng điểm capture thực tế được gọi bên trong `_sponsored_present` (hoặc `dump_ui_xml`), đồng thời kiểm tra chính xác hợp đồng xử lý lỗi (raise ngoại lệ fail-closed hay trả về fallback an toàn).

### 4. Natural Thumb Arc Coordinates vs Stale Hardcoded Swipe Assertions
* **Logic flow:** Trong `flows/feed_swipe_smoke.py`, hàm `_build_swipe_parameters` áp dụng hành vi vuốt ngón cái tự nhiên (natural thumb arc):
  ```python
  start_x = max(470, min(525, BASE_SWIPE_START[0] + x_offset))
  drift = 0 if jitter_px == 0 else random.randint(-35, 15)
  end_x = max(440, min(540, start_x + drift))
  ```
* **Pitfall in Unit Tests:** Ngay cả khi `x_offset == 0` (jitter_px = 0), `start_x` bị kẹp chặn dưới tại `470` và `end_x = 470`. Các test unit cũ assert toạ độ `["input", "swipe", "450", "1380", "450", "480", "650"]` (hoặc thời lượng cũ `650` thay vì `330`) sẽ fail vì toạ độ thực tế sinh ra là `["input", "swipe", "470", "1380", "470", "480", ...]`.
* **Fix:** Cập nhật assertion toạ độ sang `470` hoặc patch `_perform_feed_swipe` nếu test chỉ kiểm tra logic điều hướng/state recovery mà không cần kiểm tra chi tiết câu lệnh adb shell swipe.

### 5. Unmocked Sleep trong Recovery Flows Gây Timeout Suite (>110s-120s)
* **Logic flow:** Các flow phục hồi (như `_maybe_prepare_after_launcher_baseline` -> `_relaunch_and_poll_tiktok_focus` -> `force_stop_and_relaunch_tiktok`) có `after_launch_delay_seconds=6.0`, `between_delay_seconds=2.0` và retry polling `2.0s`.
* **Pitfall in Unit Tests:** Nếu test không patch `time.sleep` hoặc mock `force_stop_and_relaunch_tiktok` (ví dụ `test_baseline_packageinstaller_deny_recovers_when_tiktok_returns_to_launcher`), test đơn lẻ có thể kéo dài >22 giây, làm tổng thời gian chạy cả file test (184 items) vượt trần timeout CI/gate (110s/120s).
* **Fix:** Luôn patch `time.sleep` hoặc mock component relaunch/device_prepare trong các test recovery không đo đạc thời gian thực. Để debug nhanh test nào gây treo/timeout, chạy in-process với `threading.Thread(target=faulthandler.dump_traceback)` kèm `pytest.main(["-s", ...])`.

