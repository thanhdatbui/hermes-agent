# Case UI-50: TikTok 46.x Relation Recycler ID `id/uvz` & Follow Button ID `id/u2f`

## Hiện trường & Triệu chứng (Máy 19)
- **Quy trình**: Follow TikTok (`tiktok-follow`, Mode 2 anchor/follower flow).
- **Thiết bị**: Máy 19 | Serial: `ce0216027451853102` | Nick: `hoanghan27093` | Anchor: `phammai1805`.
- **Triệu chứng**: Dừng phiên báo Farm Alert đỏ `MANUAL_REVIEW: mở tab Đã follow fail cho phammai1805 sau ladder (lần 2)`.
- **Thực tế UI**: Màn hình thiết bị đã mở chính xác profile `phammai1805`, tab `Đã follow 176` đã được chọn (`selected=true`, underline đậm) và RecyclerView danh sách người dùng đã render đầy đủ các hàng kèm nút `Follow lại` / `Follow`.

## Nguyên nhân gốc rễ (Root Cause)
1. **Selector Drift - Relation Recycler View**:
   - Trên TikTok 46.x mới, container danh sách quan hệ Following/Follower đổi resource-id sang `com.ss.android.ugc.trill:id/uvz`.
   - Trong `follow_runner/core/selectors.py`, tuple `FOLLOWER_LIST_RECYCLER_IDS` trước đó chỉ liệt kê:
     `("com.ss.android.ugc.trill:id/u5r", "com.ss.android.ugc.trill:id/u_q", "com.ss.android.ugc.trill:id/uoc", "com.ss.android.ugc.trill:id/uo1", ...)`
   - Trong `mode2_follow_followers.py`:
     ```python
     has_recycler = any(
         node.get("resource_id") in FOLLOWER_LIST_RECYCLER_IDS for node in nodes
     )
     if has_recycler:
         return "invalid" if selected_count == "0" else "populated"
     if selected_count != "0":
         return "invalid"
     ```
     Do thiếu `id/uvz`, `has_recycler` trả về `False`. Vì `selected_count == "176"` (khác 0), hàm trả về `"invalid"`.
   - Kết quả: `_on_follower_list(nodes)` trả về `False`, vòng lặp polling 10s trong `_open_following_tab` bị timeout, kích hoạt ladder lần 2 và dừng phiên với lỗi `mở tab Đã follow fail`.

2. **Selector Drift - Follow Button in Follower/Following Rows**:
   - Các nút bấm hành động quan hệ trên từng hàng tài khoản (`Follow` / `Follow lại`) mang resource-id mới `com.ss.android.ugc.trill:id/u2f`.
   - Trong `selectors.py`, `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trước đó chỉ có `id/tcj`, `id/thb`, `id/tvn`, `id/tum`.
   - Nếu không cập nhật `id/u2f`, sau khi mở tab thành công thì `_cluster_follower_rows` và `_follow_button_for_row` cũng không nhận diện được nút follow.

## Giải pháp (Fix)
1. **`follow_runner/core/selectors.py`**:
   - Thêm `"com.ss.android.ugc.trill:id/uvz"`, `":id/uvz"`, `"id/uvz"` vào `FOLLOWER_LIST_RECYCLER_IDS`.
   - Thêm `"com.ss.android.ugc.trill:id/u2f"`, `":id/u2f"`, `"id/u2f"` vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`.

2. **Regression Tests**:
   - `test_mode2_follow_followers.py`:
     - `test_classify_follower_surface_supports_recycler_id_uvz`: Kiểm tra `_classify_follower_surface` trả về `"populated"`.
     - `test_follow_button_for_row_supports_id_u2f`: Kiểm tra `_follow_button_for_row` bắt đúng nút `id/u2f`.
     - `test_cluster_follower_rows_supports_id_u2f`: Kiểm tra `_cluster_follower_rows` ghép đúng hàng và nút `id/u2f`.
     - `test_m19_following_screen_regression_uvz_and_u2f`: Fixture toàn diện dựa trên hiện trường XML Máy 19.
   - `test_mode2_following.py`:
     - `test_open_following_tab_supports_id_uvz_and_id_u2f`: Kiểm tra `_open_following_tab` thành công với layout mới.
