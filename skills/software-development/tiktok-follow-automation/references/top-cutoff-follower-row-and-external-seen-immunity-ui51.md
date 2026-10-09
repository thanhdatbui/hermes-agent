# Case UI-51: Top-Cutoff Follower Row Exclusion & Session External Seen Immunity

## Bối Cảnh Sự Cố (Farm Alert)
- **Script:** Follow TikTok (`tiktok-follow`) tại `D:/Taadaa/tiktok-follow`
- **Máy:** 36 | **Serial:** `ce10160ac8f1962305` | **Nick:** `phuong.anh.868`
- **Triệu chứng:** `MANUAL_REVIEW: follower row không có nút follow semantic`
- **Màn hình hiện trường:** Đang quét danh sách Following của anchor `hadang0725` (tab "Đã follow 47").

## Triệu Chứng & Root Cause
1. **Top-Cutoff Row khi cuộn danh sách:**
   - Trong quá trình lướt danh sách follower/following ở Mode 2, sau khi follow/skip các row ở batch trên, danh sách cuộn xuống.
   - Row ở đỉnh danh sách (ví dụ `knorrvietnam`) bị trôi dần lên trên ra khỏi viewport của scrollable container (`RecyclerView` `id/uo1` / `id/u5r` / `id/uvz` hoặc `ViewPager`).
   - Trong dump XML uiautomator, text desc của row chỉ còn sót lại vài pixel ở mép đỉnh container (`bounds=[252, 337, 471, 340]`), trong khi nút quan hệ (`id/tum` / `id/tvn` / `id/tcj`) đã trôi hoàn toàn lên trên ra khỏi viewport (`follow_button is None`).
2. **Thiếu cơ chế lọc Top-Cutoff trong `missing_button_rows`:**
   - Trước đây, `mode2_follow_followers.py` chỉ có cơ chế loại trừ row bị cắt ở mép đáy màn hình (`bottom_cutoff_y = max_screen_y - 180`).
   - Hoàn toàn chưa có cơ chế loại trừ row bị cắt ở mép đỉnh danh sách (`top_cutoff_y`).
   - Khi tính toán `missing_button_rows`, row `knorrvietnam` (`cluster_y=(337, 340)`) bị xem là row bình thường trong màn hình nhưng thiếu nút bấm, lập tức kích hoạt fail-closed `MANUAL_REVIEW: follower row không có nút follow semantic`, ngắt phiên oan và giam lock hiện trường dù toàn bộ các row hợp lệ bên dưới (`v.danh3198`, `headandshoulders_vn`) đều có nút Follow đầy đủ.
3. **Thiếu miễn trừ cho external nick đã duyệt (`session_external_seen`):**
   - `knorrvietnam` là UID ngoài (external) đã được nhận diện và skip ở batch cuộn trước (`session_external_seen`), nhưng `missing_button_rows` không kiểm tra tập này nên vẫn bắt lỗi layout khi row bị trôi nút ở lần dump sau.

## Giải Pháp Chuẩn (Case Fix)
1. **Hàm `_find_top_cutoff_y(nodes)`:**
   - Quét tọa độ `bounds[1]` của scrollable container (`FOLLOWER_LIST_RECYCLER_IDS` như `id/u5r`, `id/uo1`, `id/uvz`, hoặc `FOLLOWER_RELATION_VIEWPAGER_ID`, class `RecyclerView` / `ViewPager`).
   - Fallback sang mép dưới của relation tab header (`android:id/text1` selected=True: `tab_bottom = b[1] + b[3]`). Lưu ý trong consumer này, `parse_nodes` trả về bounds dạng `(x, y, w, h)`.
2. **Hàm `_is_top_cutoff_row(r, top_cutoff_y)`:**
   - Trả về `True` nếu cụm tọa độ `cluster_y` chạm mép đỉnh container: `c_top <= top_cutoff_y + 10` hoặc `c_bot <= top_cutoff_y + 70`.
   - Hoặc chiều cao cụm text bị co cụm dị dạng do trôi viền: `(c_bot - c_top) < 30`.
3. **Hàm `_is_bottom_cutoff_row(r, bottom_cutoff_y)`:**
   - Tách biệt logic bottom cutoff rõ ràng: `c_bot >= bottom_cutoff_y or c_top >= (bottom_cutoff_y - 70)`.
4. **Cập nhật bộ lọc `missing_button_rows` trong `run_mode2`:**
   ```python
   missing_button_rows = [
       r for r in rows
       if r.get("follow_button") is None
       and _normalize_handle(r.get("handle", "")) != active_account
       and not state.is_followed(r.get("handle", ""))
       and not state.is_skipped(r.get("handle", ""))
       and _normalize_handle(r.get("handle", "")) not in session_external_seen
       and not _is_top_cutoff_row(r, top_cutoff_y)
       and not _is_bottom_cutoff_row(r, bottom_cutoff_y)
   ]
   ```
   - Bảo toàn 100% tính fail-closed: Các row hợp lệ nằm ở giữa màn hình nếu thực sự bị thiếu nút bấm hoặc hỏng layout vẫn bị bắt và đưa vào `MANUAL_REVIEW`.
