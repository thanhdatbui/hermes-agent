# Case UI-50: TikTok 46.x Following-List RecyclerView `id/uvz` & Follow Button `id/u2f`

## Triệu chứng & Bối cảnh
- **Farm Alert:** `[MÁY 19] DỪNG PHIÊN: MANUAL_REVIEW: mở tab Đã follow fail cho phammai1805 sau ladder (lần 2)`
- **Thiết bị:** Máy 19 | Nick: `hoanghan27093` | Anchor: `phammai1805`
- **Màn hình thực tế:** Profile `phammai1805` đã được mở, tab "Đã follow 176" đang active (`selected=true`), hiển thị danh sách người dùng đầy đủ. Nhưng runner kết luận `MANUAL_REVIEW`.

## Nguyên nhân gốc (Root Cause)
1. **RecyclerView ID drift:**
   - Trong `m19_dump.xml`, danh sách cuộn sử dụng RecyclerView:
     `res_id="com.ss.android.ugc.trill:id/uvz" cls="androidx.recyclerview.widget.RecyclerView"`
   - `FOLLOWER_LIST_RECYCLER_IDS` trong `follow_runner/core/selectors.py` trước đó chỉ có `id/u5r`, `id/u_q`, `id/uoc`, `id/uo1`.
   - Hàm `_classify_follower_surface(nodes)` kiểm tra `has_recycler` bị `False`. Vì tab header mang text "Đã follow 176" (`selected_count != "0"`), hàm rơi vào nhánh `if selected_count != "0": return "invalid"`.
   - Dẫn đến `_on_follower_list(nodes)` trả về `False`, khiến `_open_following_tab` đánh giá mở tab thất bại qua 2 lần thử của ladder recovery và escalate `MANUAL_REVIEW`.

2. **Follow Button ID drift:**
   - Trong mỗi row người dùng trên RecyclerView `id/uvz`, nút quan hệ mang:
     `res_id="com.ss.android.ugc.trill:id/u2f" cls="android.widget.Button" text="Follow lại"` hoặc `"Follow"`
   - `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py` trước đó chỉ có `id/tcj`, `id/thb`, `id/tvn`, `id/tum`.
   - Khi thiếu `id/u2f`, `_cluster_follower_rows(nodes)` nhận diện được txt_user_name và txt_desc nhưng không tìm thấy nút follow hợp lệ (`follow_button: None`), khiến các hàng không thể tap follow.

## Giải pháp chuẩn
1. **Mở rộng selector trong `follow_runner/core/selectors.py`:**
   ```python
   FOLLOWER_LIST_RECYCLER_IDS = (
       "com.ss.android.ugc.trill:id/u5r", "com.ss.android.ugc.trill:id/u_q", "com.ss.android.ugc.trill:id/uoc", "com.ss.android.ugc.trill:id/uo1", "com.ss.android.ugc.trill:id/uvz",
       ":id/u5r", ":id/u_q", ":id/uoc", ":id/uo1", ":id/uvz", "id/u5r", "id/u_q", "id/uoc", "id/uo1", "id/uvz",
   )
   
   FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS = (
       "com.ss.android.ugc.trill:id/tcj", "com.ss.android.ugc.trill:id/thb", "com.ss.android.ugc.trill:id/tvn", "com.ss.android.ugc.trill:id/tum", "com.ss.android.ugc.trill:id/u2f",
       ":id/tcj", ":id/thb", ":id/tvn", ":id/tum", ":id/u2f", "id/tcj", "id/thb", "id/tvn", "id/tum", "id/u2f",
   )
   ```

2. **Regression tests bổ sung:**
   - `test_classify_follower_surface_supports_recycler_id_uvz`: kiểm chứng `_classify_follower_surface` trả về `"populated"` và `_on_follower_list=True`.
   - `test_follow_button_for_row_supports_id_u2f`: kiểm chứng `_follow_button_for_row` bắt đúng nút `id/u2f` (Follow lại / Follow).
   - `test_cluster_follower_rows_supports_id_u2f`: kiểm chứng gán đúng nút `id/u2f` vào cluster hàng.
   - `test_m19_following_screen_regression_uvz_and_u2f`: regression test tổng hợp từ dump thực tế.
   - `test_open_following_tab_supports_id_uvz_and_id_u2f`: kiểm chứng `_open_following_tab` thành công với layout mới.
