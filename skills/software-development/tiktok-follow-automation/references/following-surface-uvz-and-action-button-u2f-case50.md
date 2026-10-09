# Case UI-50: TikTok 46.x Following Surface Selectors (`id/uvz` & `id/u2f`)

## Tình huống & Triệu chứng
- **Hiện tượng:** Farm Alert đỏ dừng phiên tại Máy 19 (Nick `hoanghan27093`, anchor `phammai1805`):
  `MANUAL_REVIEW: mở tab Đã follow fail cho phammai1805 sau ladder (lần 2)`
- **Thực tế trên thiết bị:** Màn hình máy thực tế đã mở đúng profile anchor và tab "Đã follow 176" đang hiển thị active (`selected=true`) cùng danh sách người dùng với các nút Follow / Follow lại ("Fail đâu hiện đúng mà").

## Phân tích Nguyên nhân gốc rễ (Root Cause)
1. **RecyclerView ID mới trên TikTok 46.x:**
   - Trong XML dump uiautomator (`atx_session`), node danh sách có resource-id:
     `com.ss.android.ugc.trill:id/uvz` (`class="androidx.recyclerview.widget.RecyclerView"`).
   - Trong `follow_runner/core/selectors.py`, tuple `FOLLOWER_LIST_RECYCLER_IDS` trước đó chỉ có `id/u5r`, `id/u_q`, `id/uoc`, `id/uo1`, thiếu hoàn toàn `id/uvz`.
   - Trong `_classify_follower_surface(nodes)`:
     ```python
     has_recycler = any(
         node.get("resource_id") in FOLLOWER_LIST_RECYCLER_IDS for node in nodes
     )
     if has_recycler:
         return "invalid" if selected_count == "0" else "populated"
     if selected_count != "0":
         return "invalid"
     ```
     Vì `has_recycler` trả về `False` và `selected_count` là `"176"` (`!= 0`), hàm trả về `"invalid"`.
   - `_on_follower_list(nodes)` do đó trả về `False`. Vòng lặp polling 10s trong `_open_following_tab` timeout và trả về `False`, kích hoạt ladder recovery rồi báo lỗi dừng phiên.

2. **Follow Button ID mới:**
   - Nút quan hệ trên các hàng tài khoản của danh sách Following mang resource-id:
     `com.ss.android.ugc.trill:id/u2f` (`class="android.widget.Button"`, text `Follow lại` / `Follow`).
   - Tuple `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trước đó chỉ có `id/tcj`, `id/thb`, `id/tvn`, `id/tum`. Nếu không cập nhật, sau khi mở được tab thì hàm `_follow_button_for_row` và `_cluster_follower_rows` cũng sẽ không nhận diện được nút follow.

## Giải pháp chuẩn hóa
1. Cập nhật `follow_runner/core/selectors.py`:
   - `FOLLOWER_LIST_RECYCLER_IDS`: thêm `"com.ss.android.ugc.trill:id/uvz"`, `":id/uvz"`, `"id/uvz"`.
   - `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`: thêm `"com.ss.android.ugc.trill:id/u2f"`, `":id/u2f"`, `"id/u2f"`.
2. Bổ sung regression unit tests:
   - `test_classify_follower_surface_supports_recycler_id_uvz`
   - `test_follow_button_for_row_supports_id_u2f`
   - `test_cluster_follower_rows_supports_id_u2f`
   - `test_m19_following_screen_regression_uvz_and_u2f`
   - `test_open_following_tab_supports_id_uvz_and_id_u2f`
3. Cập nhật tài liệu:
   - Ghi nhận Case UI-50 vào `docs/farm-automation-cases.md` và `docs/uiautomator.md`.
