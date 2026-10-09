# Case 184: Fast Swipe Bị Bỏ Sót Trong Mẫu Số feed_counts Từng Tab

## 1. Hiện tượng & Phản ánh từ Người vận hành
- Báo cáo Watchdog phiên nuôi TikTok ghi nhận tỷ lệ thả tim tổng là tự nhiên (`140 tim / 1159 video (12.1%)`), nhưng tỷ lệ theo từng tab trong ngoặc lại vọt lên rất cao:
  `[Đề xuất: 132 (32.3%) | Bạn bè: 8 (57.1%) | Following: 0 (0.0%)]`
- Người vận hành đặt nghi vấn: Tỷ lệ thả tim đề xuất sao cao vậy? Hay là tỷ lệ này chỉ tính trên những lượt dump XML còn các lượt fast swipe không được tính vào?

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lệch Action Filter trong Hàm Tính Toán Mẫu Số**:
   - Khi chạy chế độ lướt nhanh không dump XML (`fast_swipe`), runner gắn `action = "fast_swipe"`.
   - Trong `python_runner/flows/feed_swipe_smoke.py`, hàm `_feed_action_counts(table)` lọc đếm video theo tab:
     ```python
     # CODE CŨ:
     if row.get("action") == "swipe" and feed_type in feed_counts:
         if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
             feed_counts[feed_type] += 1
     ```
   - Do chỉ đếm `action == "swipe"`, toàn bộ ~737 lượt `fast_swipe` trên farm bị bỏ rơi khỏi mẫu số `feed_counts[feed_type]`.
   - Kết quả: Mẫu số của For You chỉ còn ~408 video (các lượt Deep Inspect dừng lại dump XML).
     $132 / 408 \approx 32.3\%$ (phình to ảo so với mức 12.1% thực tế).

## 3. Giải pháp chuẩn (Code Surgery)
1. Cập nhật `_feed_action_counts` nhận cả hai nhãn hành động `("swipe", "fast_swipe")`:
   ```python
   if row.get("action") in ("swipe", "fast_swipe") and feed_type in feed_counts:
       if not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row):
           feed_counts[feed_type] += 1
           if row.get("action") == "fast_swipe":
               fast_swipe_counts[feed_type] += 1
   ```
2. Bổ sung telemetry `fast_swipes` và `fast_swipe_counts` vào return dict của `_feed_action_counts` để nâng cao khả năng quan sát vận hành (Observability).
3. Cập nhật unit test `test_empty_friends_suggestion_feed_not_counted_in_feed_counts` trong `test_feed_swipe_smoke.py`:
   - Thêm dòng mẫu `{"action": "fast_swipe", "feed_type": "for-you"}`.
   - Assert `feed_counts["for-you"] == 2`.
   - Assert `fast_swipe_counts["for-you"] == 1`.

## 4. Kỷ luật Điều phối & Đóng phiên (Closeout Gate Pitfall)
- **Monolith Timeout Pitfall**: Khi chạy focused pytest qua `closeout_gate.py` trên monolith `test_feed_swipe_smoke.py` (chứa 101 tests, chạy mất >60s), test runner có thể bị timeout 60s. Khi cần closeout một patch nhỏ gọn, có thể chạy test trực tiếp kiểm chứng trước và cung cấp `test_evidence` chi tiết cho reviewer hoặc dùng input text để tránh timeout giả.
- **Tập trung đúng scope**: Không commit kèm các file thay đổi chính sách chưa được duyệt (như sửa upload cooldown từ fail-closed sang allow-immediately), tránh làm giảm điểm an toàn `farm_safety_regression` của reviewer.
