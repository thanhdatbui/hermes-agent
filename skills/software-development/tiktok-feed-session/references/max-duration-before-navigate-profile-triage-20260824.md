# Triage: run plan max_duration_seconds exceeded before navigate profile

## Triệu chứng & Alert signature
- **Alert Telegram:**
  ```text
  🚨 [MÁY X] DỪNG PHIÊN
  • Script: multi-machine-feed-session
  • Tài khoản: <username>
  • Lý do: run plan max_duration_seconds exceeded before navigate profile
  • Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ
  ```
- **Hiện trường thiết bị:** TikTok vẫn đang ở màn hình feed (Đề xuất / For You) bình thường sau khi đã hoàn thành các lượt vuốt video.

## Call Chain & Cơ chế phát sinh lỗi
1. **Thiết lập Deadline:** `multi_machine_feed_session.py::_run_child` gán `child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds` (`DEFAULT_DEVICE_TIMEOUT_SECONDS = 1800.0s = 30 phút`) sau khi preflight thành công.
2. **Vòng lặp Feed Session:** `feed_swipe_smoke.py::_feed_session_flow` thực hiện chuỗi lướt video ngẫu nhiên theo `_session_targets` (mặc định 8–11 video). Trên thiết bị Samsung Galaxy S7:
   - Mỗi video tốn: `watch_seconds` (2–8s) + `swipe_duration` (0.5s) + `capture_screenshot` (~50s) + `dump_ui_xml` (~20s) + kiểm tra bàn phím/popup.
   - Tổng thời gian tích lũy cho 1 chu kỳ video có thể lên đến 90–110s. Với 11 video + kiểm tra popup định kỳ, tổng thời gian đạt xấp xỉ ~1750–1800s.
3. **Trigger điểm nghẽn:** Sau khi kết thúc vòng lặp `for swipe_count in range(1, selected_total_videos + 1):`, luồng gọi `_verify_profile_after_session(ctx)`.
4. `_verify_profile_after_session` gọi `tap_navigation_target(CalibrationTarget("profile", ...))`.
5. Dòng đầu tiên của `tap_navigation_target` gọi `ensure_run_plan_deadline(ctx.config, f"navigate {target.name}")`.
6. Tại thời điểm này `time.monotonic() >= _deadline_monotonic`, hàm quăng `RunPlanDeadlineExceeded("run plan max_duration_seconds exceeded before navigate profile")`, làm phiên dừng ngay trước khi chuyển sang tab Hồ sơ.

## Phương án xử lý
1. **Hiệu chỉnh Budget Video (Khuyên dùng):**
   - Giảm dải video ngẫu nhiên `FEED_SESSION_MIN_TOTAL_VIDEOS` / `FEED_SESSION_MAX_TOTAL_VIDEOS` từ `8–11` về `6–8` hoặc `7–9`.
   - Giúp phiên hoàn tất an toàn trong 15–20 phút, giảm quá nhiệt và tràn RAM trên máy S7.
2. **Tăng Timeout Per-device:**
   - Nâng `DEFAULT_DEVICE_TIMEOUT_SECONDS` từ `1800.0` (30 phút) lên `2100.0` (35 phút) trong `multi_machine_feed_session.py` nếu muốn giữ nguyên target video cao.
