# TikTok Video Pin Swap & Rollback Safety Protocol (2026-10-31)

## 1. Bản chất sự cố lủng Slot Ghim khi Swap
Khi hoán đổi (swap) bài ghim (hạ bài ghim ít view nhất để ghim bài mới nhiều view hơn):
- **Bẫy đối soát chuỗi cứng `raw_text`:** Sau khi bấm "Bỏ ghim khỏi đầu" cho bài cũ, danh sách video trên app TikTok dịch chuyển (shift layout) hoặc các badge/text view có thể thay đổi nhẹ. Nếu tìm lại bài đích (`new_target`) bằng cách so sánh chuỗi chính xác `t["raw_text"] == target["raw_text"]`, selector sẽ bị trượt (trả về `None`) và văng lỗi `TARGET_NOT_FOUND_AFTER_UNPIN`.
- **Hậu quả mất bài ghim:** Bài cũ đã bị tháo ra nhưng bài mới không ghim được, khiến profile tài khoản bị hụt số lượng video ghim (ví dụ từ 3 video rớt xuống 2 video).

## 2. Quy chuẩn thiết kế Swap 2 tầng an toàn (Safe Swap Architecture)

### Tầng 1: Tìm kiếm linh hoạt theo View & Fallback bài cao nhất
Tuyệt đối không so sánh chuỗi `raw_text` sau khi unpin. Thay vào đó:
1. Tìm theo view chuẩn:
   ```python
   new_target = next((t for t in tiles if not t["is_pinned"] and t["views"] == target["views"]), None)
   ```
2. Nếu TikTok làm tròn hiển thị số view khác đi (ví dụ 10,6K -> 10,7K), tự động fallback lấy bài chưa ghim có view cao nhất:
   ```python
   if new_target is None:
       unpinned = [t for t in tiles if not t["is_pinned"]]
       new_target = max(unpinned, key=lambda t: t["views"], default=None)
   ```

### Tầng 2: Cơ chế Tự động Rollback bảo toàn số lượng Pin
Nếu không tìm thấy `new_target` hoặc lệnh `PIN` bài mới thất bại / không xác nhận được (`PIN_NOT_VERIFIED`):
- **BẮT BUỘC** gọi hàm `rollback`: Quét lại UI, tìm lại bài `lowest` vừa bị hạ ghim và bấm `PIN` lại để khôi phục trạng thái ban đầu.
- Ghi nhận `metrics["rollback_success"]` để giám sát, không bao giờ để kênh ở trạng thái thiếu slot ghim.

## 3. Phục hồi ATX-Agent khi Dump UI trả về Non-XML trên Samsung S7
Nếu script ghim báo lỗi `UI_DUMP_INVALID: adapter returned non-XML UI state` hoặc `/dumpUI` trả về rỗng:
- Gọi hàm `reset_atx_agent(dev, timeout=15.0)` từ `automation_core.persistent_ui` để dọn process treo và kích hoạt lại stub daemon trước khi retry mở profile.
