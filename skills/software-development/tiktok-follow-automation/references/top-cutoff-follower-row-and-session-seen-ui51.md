# Top-Cutoff Follower Row Exclusion and Session External Seen Immunity (Case UI-51)

## Context & Problem Statement

Trong Mode 2 (`mode2_follow_followers.py`), danh sách Followers/Following được duyệt theo từng batch viewport sau mỗi lần cuộn (`_scroll_follower_list`).
Khi danh sách cuộn xuống, các row ở batch trước trôi dần lên trên ra khỏi khung nhìn.
Tại đỉnh scrollable container (`top_cutoff_y` ~ 337 đối với RecyclerView `id/uo1`, `id/u5r`, `id/uvz` hoặc ViewPager), text username/desc (`id/txt_desc` hoặc `id/txt_user_name`) có thể chỉ còn lọt lại một vài pixel (ví dụ `bounds=[252, 337, 471, 3]` như nick `knorrvietnam` trên Máy 36).
Trong khi đó, nút quan hệ (`id/tcj`, `id/tvn`, `id/tum`, `id/u2f`) đã trôi hoàn toàn lên trên ra ngoài viewport XML (`r["follow_button"] is None`).

Trước đây, hệ thống chỉ có bộ lọc loại trừ row ở mép đáy (`bottom_cutoff_y = max_screen_y - 180`):
```python
missing_button_rows = [
    r for r in rows
    if r["follow_button"] is None
    and _normalize_handle(r.get("handle", "")) != active_account
    and not state.is_followed(r.get("handle", ""))
    and not state.is_skipped(r.get("handle", ""))
    and r.get("cluster_y", (0, 0))[1] < bottom_cutoff_y
    and r.get("cluster_y", (0, 0))[0] < (bottom_cutoff_y - 70)
]
```
Do thiếu kiểm tra mép trên (`top_cutoff_y`), row bị cắt ở đỉnh (`knorrvietnam` với `cluster_y = (337, 340)`) bị xem là row bình thường trong màn hình nhưng thiếu nút bấm, lập tức kích hoạt fail-closed `MANUAL_REVIEW: follower row không có nút follow semantic`, ngắt phiên oan và giam lock hiện trường.

Ngoài ra, `knorrvietnam` là nick ngoài (external) đã được xử lý skip ở batch trước và lưu trong `session_external_seen`. Việc thiếu kiểm tra `session_external_seen` trong `missing_button_rows` khiến các nick ngoài đã duyệt qua vẫn có thể gây dừng phiên khi bị trôi nút sau scroll.

## Solution & Geometry Contract

1. **Top Cutoff Resolution (`_find_top_cutoff_y`)**:
   - Tự động tìm tọa độ `top_cutoff_y` từ `bounds[1]` của container scrollable (`FOLLOWER_LIST_RECYCLER_IDS` như `id/u5r`, `id/uo1`, `id/uvz`, hoặc `FOLLOWER_RELATION_VIEWPAGER_ID` hoặc class `RecyclerView` / `ViewPager`).
   - Fallback: mép dưới của relation tab header (`android:id/text1` có `selected=true` hoặc `FOLLOWER_TAB_RESOURCE_ID`).

2. **Top-Cutoff Row Detection (`_is_top_cutoff_row`)**:
   - Một row bị xem là top-cutoff nếu:
     + `cluster_y[0] <= top_cutoff_y + 10` hoặc `cluster_y[1] <= top_cutoff_y + 70` (chạm mép container phía trên).
     + Hoặc chiều cao cụm text bị co cụm bất thường (`cluster_y[1] - cluster_y[0] < 30`).

3. **Session External Seen Immunity**:
   - Bỏ qua các row có `_normalize_handle(r.get("handle", "")) in session_external_seen` khỏi `missing_button_rows`.

4. **Fail-Closed Contract Intact**:
   - Các row nằm trọn vẹn ở giữa màn hình (`top_cutoff_y + 70 < cluster_y[0] < cluster_y[1] < bottom_cutoff_y - 70`) nếu thực sự thiếu follow button và không phải self-account vẫn bị bắt và chuyển `MANUAL_REVIEW`.
