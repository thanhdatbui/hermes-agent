# Case 184: Lệch Mẫu Số feed_counts Từng Tab Do Fast Swipe Mang Action "fast_swipe"

## Hiện tượng
Người vận hành phát hiện và thắc mắc trên báo cáo Watchdog Feed Session:
```text
• Thả tim: 140 tim / 1159 video (12.1%) [Đề xuất: 132 (32.3%) | Bạn bè: 8 (57.1%) | Following: 0 (0.0%)]
```
Tỉ lệ thả tim tổng thể toàn farm hiển thị rất đẹp và tự nhiên (`12.1%`), nhưng tỉ lệ thả tim bóc tách từng tab trong ngoặc vuông lại cao bất thường (`Đề xuất: 32.3%`, `Bạn bè: 57.1%`).

## Nguyên nhân cốt lõi (Root Cause)
1. **Khác biệt nhãn action:**
   - Khi chạy luồng **Fast Swipe** (lướt nhanh không dump XML để tối ưu tốc độ và tránh phát hiện), hàm `feed_swipe_smoke.py` ghi nhận kết quả với `"action": "fast_swipe"` (tại các dòng ~21827, ~21980).
   - Khi chạy luồng **Deep Inspect** (dừng lại dump XML, soi nút like, soi comment, bóc view), kết quả ghi nhận `"action": "swipe"`.
2. **Lọc sót trong `_feed_action_counts()` (`feed_swipe_smoke.py`, ~dòng 12617):**
   ```python
   for row in table:
       feed_type = row.get("feed_type")
       if row.get("action") == "swipe" and feed_type in feed_counts:
           if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
               feed_counts[feed_type] += 1
   ```
   Hàm chỉ kiểm tra `row.get("action") == "swipe"`, dẫn đến **toàn bộ các lượt Fast Swipe (~65-70% video) bị loại bỏ khỏi `feed_counts` của từng tab**.
3. **Mẫu số lệch giữa tổng và chi tiết:**
   - Mẫu số tổng ngoài ngoặc (`1159 video`) đọc từ `total_swipes_completed` trong `summary.txt` (tính đủ cả Fast Swipe lẫn Deep Inspect). Do đó: $140 / 1159 = 12.08\% \approx 12.1\%$.
   - Vì Fast Swipe không dump XML nên **chỉ có video Deep Inspect mới có thể được thả tim**.
   - Mẫu số trong ngoặc `tot_fy_swipes` đọc từ `feed_counts["for-you"]` (chỉ gồm các video Deep Inspect ~408 video). Do đó: $132 / 408 = 32.35\% \approx 32.3\%$.
   - Tab Bạn bè: $8 \text{ tim} / 14 \text{ video Deep Inspect} = 57.14\% \approx 57.1\%$.

## Hướng xử lý chuẩn (Patch Contract)
Khi cần hiển thị tỉ lệ thả tim từng tab phản ánh chính xác trên tổng số video của tab đó (thay vì chỉ tính trên video Deep Inspect):
Cập nhật điều kiện lọc trong `_feed_action_counts`:
```python
# Cũ:
if row.get("action") == "swipe" and feed_type in feed_counts:

# Mới:
if row.get("action") in ("swipe", "fast_swipe") and feed_type in feed_counts:
```
Điều này đảm bảo `feed_counts[feed_type]` tính đủ cả Fast Swipe, đưa mẫu số từng tab khớp với tổng số video thực tế đã lướt qua trên tab đó.
