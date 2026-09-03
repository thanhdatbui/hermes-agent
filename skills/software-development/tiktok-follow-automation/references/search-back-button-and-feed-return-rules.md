# Search Screen Back Button & Feed Navigation Contract (TikTok 46.x)

## Bối Cảnh & Vấn Đề (Anti-Pattern)
Khi runner follow UID tiếp theo (hoặc giữa các lượt trong Module 1 / Module 2), hàm `_back_to_feed` / `ensure_feed_for_follow` cần đưa giao diện từ màn hình tìm kiếm (Search history / Autocomplete) quay về lại Feed (`Trang chủ` selected=True).

Trên các phiên bản TikTok 46.x cập nhật trên Farm (ví dụ Máy 57):
1. Nút Back icon ở góc trên bên trái màn hình Search mang resource-id `com.ss.android.ugc.trill:id/bq8` (trước đó là `id/bow`, `id/bqp`, `id/back_btn`) với toạ độ `bounds=(18, 84, 132, 132)` (`x < 250, y < 250`).
2. Nếu danh sách whitelist nút Back không chứa `id/bq8`, runner sẽ fallback sang phím Back cứng (`adapter.press_back()`).
3. Khi bàn phím mềm Samsung hoặc khay gợi ý đang mở, phím Back cứng (keycode 4) chỉ đóng bàn phím mà không thoát màn hình Search. Sau 4 lần gửi Back cứng, runner không thể trở về Feed và kích hoạt dừng phiên an toàn fail-closed: `MANUAL_REVIEW: không chứng minh được Feed trước Search UID`.

## Quy Tắc Chuẩn (Case Fix Contract)
1. **Whitelist Resource-ID Nút Back Màn Hình Search:**
   - Bắt buộc kiểm tra danh sách đầy đủ: `("id/bow", "id/bqp", "id/bq8", "id/back_btn")`.
   - Kết hợp ràng buộc toạ độ góc trên bên trái: `n["bounds"][0] < 250 and n["bounds"][1] < 250`.
   - Ưu tiên tap nút gần góc `(0, 0)` nhất (`sort(key=lambda n: n["bounds"][0] ** 2 + n["bounds"][1] ** 2)`).
2. **Xác Thực Sau Tap Back:**
   - Sau khi tap nút Back icon, đợi UI cập nhật và dump lại XML.
   - Chứng minh màn hình Feed với:
     - `homes = [n for n in nodes if n["content_desc"] in {"Trang chủ", "Home"} and n["selected"] is True]`
     - `profiles = [n for n in nodes if n["content_desc"] in {"Hồ sơ", "Profile"} and n["selected"] is False]`
     - Không có follower recycler (`FOLLOWER_LIST_RECYCLER_IDS`).
