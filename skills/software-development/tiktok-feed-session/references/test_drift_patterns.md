# TikTok Feed Session Smoke - Test Drift Patterns & Mock Pitfalls

Khi cập nhật hoặc sửa chữa bộ test trong `python_runner/tests/test_feed_swipe_smoke.py`, cần lưu ý các điểm trôi lệch schema và cơ chế mock sau:

### 1. Schema cột của `build_feed_swipe_summary`
Khi bổ sung tính năng mới vào summary (ví dụ `comment_peeked`), schema danh sách key của summary row sẽ thay đổi thứ tự:
- Vị trí: `... -> "liked" -> "followed" -> "comment_peeked" -> "sponsored_skipped" -> ...`
- Kiểm tra lại toàn bộ danh sách key trong `test_build_feed_swipe_summary_columns` khi thêm trường mới.

### 2. Dung sai thời gian vuốt (Swipe duration jitter)
- `_perform_feed_swipe` áp dụng jitter ngẫu nhiên cho tọa độ và duration:
  - Base duration thường dao động rộng hơn dự tính (ví dụ từ 400ms đến 850ms tùy cấu hình).
  - Không hardcode khoảng hẹp `550 <= duration_ms <= 750` trong assertion trừ khi mock cố định giá trị `random.uniform` / `random.randint`.

### 3. Điều kiện kích hoạt cuộn ngược Profile (`_verify_profile_after_session`)
- Nhánh cuộn `ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"])` có điều kiện tiên quyết: `profile_screen_confirmed == True`.
- `_profile_screen_confirmed_from_xml(xml_text)` chỉ trả về `True` khi tìm thấy node chứa text hoặc content-desc là `"Hồ sơ"` / `"Profile"` **và có thuộc tính `selected="true"`**.
- **Pitfall khi viết mock XML**: Nếu mock XML trang Profile bị cuộn mà không chứa tab bar với node `<node text="Hồ sơ" selected="true" .../>`, hàm sẽ nhận định UI chưa vào màn Profile và thực hiện `tap_navigation_target` (re-navigate) thay vì cuộn lên!

### 4. Tỷ lệ Like mặc định (`DEFAULT_FEED_LIKE_RATES`)
- Tab `FEED_TYPE_FOLLOWING`: mặc định là `35` (tránh nhầm với cấu hình cũ 50).
- Tab `FEED_TYPE_FRIENDS`: mặc định là `45` (tránh nhầm với cấu hình cũ 80).
- Tab `FEED_TYPE_FOR_YOU`: mặc định là `8`.
