# Case UI-76: Layout Drift TikTok 47.0.3 Tab Following (Empty Title id/yx1) & Safe-Skip Anchor

## 1. Hiện tượng & Triệu chứng
- Khi chạy Mode 2 (`mode2_follow_followers.py`), bot tìm anchor (ví dụ `@hiencao179`) và bấm vào tab "Đã follow" (Following).
- Nếu anchor có danh sách Following trống (0 following) hoặc layout hiển thị tiêu đề rỗng dạng mới trên TikTok 46.x/47.x:
  - Bot bị kẹt timeout 35s tại `_open_following_tab`.
  - Hệ thống thử lại lần 2 sau ladder recovery và tiếp tục fail, văng ra `status: MANUAL_REVIEW` kèm `exit_code: 1`.
  - Watchdog gán cờ "Lỗi script/xác minh: mở tab Đã follow fail cho <anchor> sau ladder (lần 2)".

## 2. Nguyên nhân cốt lõi (Root Cause)
- Resource ID của tiêu đề danh sách rỗng (Empty Title) trên các bản TikTok mới đổi thành `com.ss.android.ugc.trill:id/yx1` (thay vì chỉ có `id/yhj` hoặc `id/yxo`).
- Hàm `_classify_follower_surface(nodes)` không nhận diện được `id/yx1`, dẫn đến việc phân loại nhầm màn hình thành `"invalid"`.
- Do surface bị coi là `invalid`, `_on_follower_list(nodes)` trả về `False`, khiến vòng lặp kiểm tra tab không thể nhận biết tab đã mở thành công và bị timeout chờ đợi `RecyclerView`.

## 3. Giải pháp & Quy chuẩn xử lý
1. **Cập nhật Selector Drift:**
   Bổ sung `id/yx1` vào danh sách nhận diện layout tiêu đề mới (`has_modern_title`) trong `_classify_follower_surface`:
   ```python
   has_modern_title = any(
       node.get("resource_id") in (
           "com.ss.android.ugc.trill:id/yhj",
           "com.ss.android.ugc.trill:id/yxo",
           "com.ss.android.ugc.trill:id/yx1",
       )
       for node in nodes
   )
   ```
2. **Nhận diện màn hình Empty:**
   Khi phát hiện `id/yx1`, surface được phân loại chuẩn thành `"empty"`. Khi đó:
   - `_on_follower_list = True`
   - `_is_zero_following_screen_or_profile = True`
   - Bot lập tức nhận diện anchor có 0 following và chủ động skip sang anchor tiếp theo trong $O(1)$.
3. **Safe-skip thay vì văng Crash/MANUAL_REVIEW:**
   Nếu anchor bị kẹt UI sau 2 lần ladder recovery, script tự động chuyển `mode2_degraded = True` và chuyển sang anchor tiếp theo thay vì ngắt toàn bộ phiên và trả về lỗi `MANUAL_REVIEW`.
