# Samsung TikTok Account Switcher Tap Dead-Space

## Bối cảnh & Hiện tượng
Trên các thiết bị Samsung Galaxy (màn hình 1080x1920, ví dụ SM-G930F/W8), khi TikTok hiển thị bottom sheet / dialog Account Switcher:
- Node container hàng (Row / Button clickable) có bề rộng đầy đủ (`bounds[2] - bounds[0] >= 600`, thường x từ 0 đến 1080).
- Tọa độ tâm của row container rơi vào `x ≈ 540`.
- Trên Samsung UI / TikTok layout, khoảng giữa `x ≈ 540` là "dead-space" trống giữa nhãn `TextView` (tên tài khoản) và badge/radio icon bên phải.
- Khi tap vào tâm hàng container (`x=540`), TikTok nuốt tap hoặc bỏ qua (không trigger chuyển tài khoản).

## Cách xử lý chuẩn (Best Practice)
Trong `feed_swipe_smoke.py` (`_find_account_switch_option`) và các module điều khiển switcher tương tự:
1. **Không tap vào tâm row container rộng:** Tránh lấy center của node nếu bề rộng container >= 600px.
2. **Ưu tiên lấy bounds của inner `TextView`:**
   Quét các child nodes trong XML (`_nodes(xml_text)`): tìm `TextView` chứa đúng tên tài khoản hoặc khớp identity (`matches_switcher_identity`).
   Nếu tìm thấy inner node có `0 < width < 600` và nằm trọn trong bounds hàng (`node.bounds[1] <= inner.bounds[1]` và `inner.bounds[3] <= node.bounds[3]`), dùng bounds của inner node làm target tap.
3. **Fallback clamp x:**
   Nếu không tìm thấy inner child, fallback clamp vùng tap: `(node.bounds[0], y1, min(node.bounds[0] + 700, max_r), y2)` thay vì click x=540.

## Bottom-Sheet Row / Navigation Bar Collision (Safe Y Point)
- **Hiện tượng:** Hàng "Thêm tài khoản" / "Add account" nằm dưới cùng của bottom sheet có bounds chạm đáy màn hình (ví dụ: `[0, 1788][1080, 1920]`).
- **Pitfall:** Tọa độ tâm theo trục Y là `(1788 + 1920) // 2 = 1854`. Tọa độ này chạm vào vùng navigation bar / cử chỉ hệ thống của Android, làm đóng bottom sheet hoặc back thay vì mở luồng đăng nhập / thêm tài khoản.
- **Quy tắc tính safe_y:**
  ```python
  safe_x = (x1 + x2) // 2
  safe_y = y1 + max(1, (y2 - y1) // 3)  # Tap 1/3 phía trên của row thay vì center
  ```
  Ví dụ với `[0, 1788][1080, 1920]`: `safe_y = 1788 + 44 = 1832` (tránh được navigation bar ở 1854).

