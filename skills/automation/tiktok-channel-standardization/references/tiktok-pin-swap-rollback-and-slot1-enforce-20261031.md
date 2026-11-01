# TikTok Pin-Top Swap Failures, Slot-1 Invariant & Rollback Architecture

## 1. Bản chất sự cố rớt bài ghim và mất Slot 1
Trong cơ chế tự động hoá ghim bài top view (`pin_top_videos.py` / `trending_pin_watchdog.py`), hai lỗi kiến trúc nghiêm trọng từng khiến kênh bị rớt bài ghim từ 3 xuống 2 hoặc bài top 1 view không chiếm được Ô số 1:

### A. Bẫy tìm lại tile theo chuỗi cứng `raw_text` sau khi Unpin
- **Hiện tượng:** Khi hạ ghim bài cũ (Lowest) để nhả slot cho bài mới cắn view (Target), lưới video của TikTok cập nhật lại cấu trúc DOM/XML.
- **Lỗi cũ:** Code cũ tìm lại tile bài mới bằng:
  ```python
  new_target = next((t for t in tiles if not t["is_pinned"] and t["raw_text"] == target["raw_text"]), None)
  ```
- **Hậu quả:** Khi lưới video dịch chuyển, text phụ trên tile (ví dụ nhãn thời lượng, số view được làm tròn lại, ký tự space/newline) thay đổi khiến `raw_text` không khớp 100%. `new_target` bị `None` $\to$ văng `TARGET_NOT_FOUND_AFTER_UNPIN`.
- **Khắc phục chuẩn O(1):**
  1. Khớp ưu tiên theo số view: `t["views"] == target["views"]`.
  2. Fallback bốc bài chưa ghim có view cao nhất: `max((t for t in tiles if not t["is_pinned"]), key=lambda t: t["views"])`.

### B. Thiếu cơ chế Rollback khi Swap thất bại
- **Hiện tượng:** Bài cũ đã bị Unpin thành công nhưng việc Pin bài mới thất bại (không tìm thấy tile hoặc Action Sheet không nảy).
- **Hậu quả:** Kênh bị **hụt mất 1 slot ghim** (từ 3 video rớt xuống 2 video) trong im lặng.
- **Khắc phục:** Bắt buộc có hàm `rollback` nội tại:
  - Nếu bất kỳ bước nào trong pha pin bài mới thất bại (`TARGET_NOT_FOUND`, `PIN_BUTTON_NOT_FOUND`, `PIN_NOT_VERIFIED`), lập tức gọi `_apply_tile_action` ghim lại chính bài `lowest` vừa unpin để bảo toàn nguyên vẹn 3 slot ghim.

### C. Bẫy cờ `not auto_swap` triệt tiêu `_enforce_top_pin_at_slot1`
- **Hiện tượng:** User yêu cầu bài view cao nhất luôn phải nằm ở video đầu tiên (Slot 1 - ngoài cùng bên trái), nhưng sau khi chạy pin/swap bài view cao nhất lại nằm ở Ô 2 hoặc Ô 3.
- **Nguyên nhân cốt lõi:**
  1. Trong hàm `pin_video_on_device`, lệnh gọi `_enforce_top_pin_at_slot1` từng bị bọc bởi:
     ```python
     if not dry_run and not auto_swap: # <-- BUG: Mặc định auto_swap=True nên enforce KHÔNG BAO GIỜ CHẠY
         _enforce_top_pin_at_slot1(...)
     ```
  2. Trong hàm `_swap_pinned_tile`, sau khi swap xong hoàn toàn không gọi `_enforce_top_pin_at_slot1`.
- **Khắc phục:**
  - Xoá hoàn toàn điều kiện `not auto_swap`. Ở cả luồng Pin mới lẫn luồng Swap, luôn gọi `_enforce_top_pin_at_slot1` ở cuối quy trình để bảo toàn Invariant: **Top 1 View = Slot 1**.
