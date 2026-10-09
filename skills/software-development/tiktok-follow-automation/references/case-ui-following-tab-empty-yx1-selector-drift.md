# Case UI: TikTok 47.0.3 Selector Drift id/yx1 Trên Tab Đã Follow Trống

## Bối cảnh & Hiện tượng (2026-09-28)
- **Triệu chứng:** Khi chạy Mode 2 (`mode2_follow_followers.py`), bot mở tab Đã follow (Following) của anchor. Anchor có danh sách Following = 0 (trống).
- **Hành vi cũ bị lỗi:**
  - `_classify_follower_surface(nodes)` chỉ nhận diện empty title button qua resource ID cũ `id/yhj` hoặc `id/yxo`.
  - Trên TikTok 46.x / 47.x, nút tiêu đề rỗng mang resource ID mới `com.ss.android.ugc.trill:id/yx1` (hoặc `:id/yx1`, `id/yx1`).
  - Do thiếu ID này, surface bị phân loại là `invalid` thay vì `empty`.
  - `_on_follower_list()` trả về `False`, khiến vòng lặp poll chờ render quá 35s deadline và văng lỗi:
    `MANUAL_REVIEW: mở tab Đã follow fail cho <anchor> sau ladder (lần 2)`.

## Bản vá Chuẩn hóa
1. **Selector Drift:**
   Thêm `id/yx1` vào danh sách `has_modern_title` trong `_classify_follower_surface()`:
   ```python
   has_modern_title = any(
       node.get("resource_id") in (
           "com.ss.android.ugc.trill:id/yhj",
           "com.ss.android.ugc.trill:id/yxo",
           "com.ss.android.ugc.trill:id/yx1",
           ":id/yx1",
           "id/yx1",
       )
       for node in titles
   )
   ```
2. **Tab Selected Retry:**
   Trong `_open_following_tab()`, nếu sau cú tap đầu mà tab chưa kịp mang trạng thái `selected=True` hoặc animation loading, tự động tap lại nút tab `android:id/text1`.
3. **Safe Degradation (Thay vì văng crash):**
   Nếu mở tab thất bại sau 2 lần ladder recovery, tự động safe-skip sang anchor tiếp theo (`mode2_degraded = True`) thay vì ném `MANUAL_REVIEW` làm gãy session.
