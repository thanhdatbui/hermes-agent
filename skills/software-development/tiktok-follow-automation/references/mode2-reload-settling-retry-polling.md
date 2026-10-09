# Mode 2 Post-Reload Profile Identity Settling Retry Polling

## Bối cảnh & Hiện tượng (Farm Alert [MÁY 7])
Khi chạy follow Mode 2 (follow follower của anchor), runner tìm kiếm anchor -> mở profile -> gọi `_ensure_anchor_followed` để follow anchor nếu chưa follow. Nếu anchor được follow, hàm thực hiện `pull_to_refresh_profile` và dump lại UI XML (`ensured_xml != profile_xml`).

Tiến trình bị dừng khẩn cấp với cảnh báo:
`hồ sơ identity mismatch sau khi reload (missing_header_handle) — từ chối tap Following`

## Nguyên nhân gốc (Root Cause)
1. Sau động tác vuốt làm mới `pull_to_refresh_profile`, UI profile trên thiết bị thực tế (Android Samsung) có hiệu ứng spring-back / settling animation (màn hình nảy nhẹ trước khi dừng ở vị trí cố định).
2. Tại thời điểm dump XML đầu tiên ngay sau vuốt, header handle `@uid` có thể tạm thời bị đẩy xuống dưới hoặc lệch tọa độ với `top_y >= 650`.
3. Hàm `_find_header_handle_node` áp đặt điều kiện chặt `top_y < 650` để loại trừ các thẻ gợi ý/video bên dưới. Khi `top_y >= 650`, hàm bỏ qua node và trả về `(None, "missing_header_handle")`.
4. Trước đây, `_open_following_tab` chỉ kiểm tra danh tính một lần duy nhất ngay sau reload mà không có cơ chế settling retry polling, dẫn đến việc fail-closed ngay lập tức và dừng phiên.

## Giải pháp chuẩn hóa (Pattern)
Trong `_open_following_tab` (`mode2_follow_followers.py`):
1. Bọc việc xác thực profile identity sau reload trong vòng lặp polling có giới hạn số lần thử:
   `retries = int(getattr(engine.cfg, "verify_reload_retries", 2) or 2)`
   `settle_attempts = max(1, retries + 1)`
2. Với `attempt > 0`:
   - `time.sleep(1.0)`
   - `profile_xml = adapter.dump_ui()` (bọc `try...except FollowAdapterError`)
   - `profile_nodes = _parse_mode2_nodes(profile_xml)`
3. Re-validate identity qua `profile_identity_from_xml` và `_find_header_handle_node(profile_nodes, uid)`.
4. Khi danh tính khớp (`target_normalized == _normalize_handle(profile_handle)` và `status == "ok"`):
   - Đánh dấu `identity_ok = True`, `break` và tiếp tục mở tab Following với `profile_nodes` đã ổn định.
5. Chỉ khi đã thử hết `settle_attempts` mà danh tính vẫn không khớp hoặc vắng mặt:
   - Ghi nhận `reason_holder.append(f"hồ sơ identity mismatch sau khi reload ({status}) — từ chối tap Following")`
   - Fail-closed trả về `False`.
