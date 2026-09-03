# Bottom-Cutoff Follower Row Exclusion and Missing Button Safety

## Context & Problem Statement

Trong Mode 2 (`mode2_follow_followers.py`), danh sách Followers/Following được duyệt theo từng batch viewport sau mỗi lần cuộn.
Khi một item ở cạnh đáy màn hình (ví dụ $y \approx 1820..1920$ trên màn hình 1080x1920), text username/desc (`txt_desc`) có thể đã lọt một phần vào viewport XML uiautomator, nhưng button quan hệ (`id/tcj`, `id/tvn`, `id/fds`) nằm thấp hơn hoặc bị cắt bởi viền dưới màn hình nên không xuất hiện trong node tree (`r["follow_button"] is None`).

Trước đây, logic kiểm tra tính toàn vẹn layout:
```python
missing_button_rows = [
    r for r in rows
    if r["follow_button"] is None
    and _normalize_handle(r.get("handle", "")) != active_account
    and not state.is_followed(r.get("handle", ""))
    and not state.is_skipped(r.get("handle", ""))
]
if missing_button_rows:
    res.status = "MANUAL_REVIEW"
    res.reason = "MANUAL_REVIEW: follower row không có nút follow semantic"
    failed = True
    break
```
sẽ ngay lập tức kích hoạt `MANUAL_REVIEW`, dừng toàn bộ phiên follow và giam lock hiện trường do hiểu lầm rằng UI bị vỡ layout hoặc thiếu nút follow.

## Solution & Geometry Contract

1. **Screen Height Resolution**:
   - Tính toán chiều cao hiển thị thực tế:
     ```python
     max_screen_y = 1920
     for n in nodes:
         if n.get("bounds"):
             max_screen_y = max(max_screen_y, n["bounds"][1] + n["bounds"][3])
     bottom_cutoff_y = max_screen_y - 180
     ```

2. **Bottom-Cutoff Row Filtering**:
   - Chỉ xem một row là `missing_button_rows` (lỗi layout nghiêm trọng cần review thủ công) nếu row đó nằm hoàn toàn bên trong vùng hiển thị an toàn phía trên:
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

3. **Lifecycle Behavior**:
   - Row bị cắt ở đáy không bị fail; runner tiếp tục xử lý các `pending` rows có button đầy đủ ở phía trên.
   - Sau khi hoàn thành batch hiện tại, runner thực hiện `_scroll_follower_list(engine)`, đưa row ở đáy lên giữa màn hình để hiển thị trọn vẹn cả text và follow button ở lần dump tiếp theo.
