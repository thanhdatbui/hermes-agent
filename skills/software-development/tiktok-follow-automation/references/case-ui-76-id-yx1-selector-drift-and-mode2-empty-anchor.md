# Case UI-76: Selector Drift `id/yx1` trên TikTok 46.x/47.x & Cơ Chế Safe-skip Mode 2 Anchor (2026-09-28)

## 1. Triệu chứng & Hiện trường
- Khi chạy follow Mode 2 trên TikTok Farm, máy dừng và báo lỗi:
  `MANUAL_REVIEW: mở tab Đã follow fail cho <anchor> sau ladder (lần 2)`
- Script bị treo trong vòng lặp poll kiểm tra danh sách Following (timeout 25-35s) dù trên thực tế tab Đã follow đã được mở thành công.

## 2. Root Cause
1. **Selector Drift tiêu đề tab rỗng:**
   - Trên TikTok phiên bản 46.x / 47.x, khi anchor có 0 Following (danh sách rỗng) hoặc layout tiêu đề kiểu mới, resource-id của nút tiêu đề rỗng bị đổi thành `com.ss.android.ugc.trill:id/yx1` (cùng dòng với `id/yhj` và `id/yxo`).
   - Hàm `_classify_follower_surface` trước đây chỉ kiểm tra `("com.ss.android.ugc.trill:id/yhj", "com.ss.android.ugc.trill:id/yxo")`. Do thiếu `id/yx1`, hàm trả về `"invalid"` thay vì `"empty"`.
   - Kết quả: `_on_follower_list` trả về `False`, khiến `_open_following_tab` coi như mở tab thất bại.
2. **Cơ chế xử lý khi mở tab fail:**
   - Trước đây khi ladder lần 2 fail, script văng `MANUAL_REVIEW` và kết thúc session với `failed = True`, kích hoạt alert giữ hiện trường không cần thiết cho trường hợp chỉ đơn thuần là anchor không load được tab.

## 3. Bản vá & Giải pháp kỹ thuật (`follow_runner/flows/mode2_follow_followers.py`)
1. **Nhận diện đúng `id/yx1`:**
   ```python
   has_modern_title = any(
       node.get("resource_id") in (
           "com.ss.android.ugc.trill:id/yhj",
           "com.ss.android.ugc.trill:id/yxo",
           "com.ss.android.ugc.trill:id/yx1",
           ":id/yx1",
           "id/yx1"
       )
       for node in titles
   )
   if len(viewpagers) == 1 and has_modern_title and len(messages) == 1:
       return "empty"
   ```
2. **Cơ chế retry tap selector:**
   - Trong vòng lặp poll `_open_following_tab`, nếu tab chưa chuyển sang trạng thái `selected` hoặc `loading`, tự động tap lại node `android:id/text1` chứa marker `"đã follow" / "following"`.
3. **Chuyển sang Safe-skip Degraded:**
   - Khi anchor mở tab fail sau lần 2, ghi nhận `res.details["mode2_degraded"] = True`, log warning và an toàn quay về feed (`_back_to_feed`), bỏ qua sang anchor tiếp theo thay vì crash `MANUAL_REVIEW`.
