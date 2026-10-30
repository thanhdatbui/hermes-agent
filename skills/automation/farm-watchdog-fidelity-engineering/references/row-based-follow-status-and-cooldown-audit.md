# Case Study: Phân Bổ & Trạng Thái Follow Toàn Farm Theo Row (Dynamic Shift Pool)

## 1. Bản Chất Báo Cáo Follow Theo Từng Row Cụ Thể
Khi user yêu cầu: *"report acc các row đi follow như nào"*, báo cáo BẮT BUỘC phải phân tách rạch ròi theo từng Row (thay vì gộp chung một cục toàn farm), với các chỉ số cốt lõi:
1. **Row đang chạy:** Xác định qua `shift_pool_cycle_state.json` và trường `row` trong `follow_result.json` của từng máy.
2. **Tổng số máy tham gia từng Row.**
3. **Số máy follow thành công (>0 lượt):** Liệt kê chi tiết (Machine, Account, Count).
4. **Số máy bị nhả follow (`FOLLOW_FAILED`):** Cơ chế Natural Re-entry Verify phát hiện nút follow bị TikTok revert ngay sau khi bấm. Tool fail-safe dừng phiên ngay để cứu acc khỏi bị phạt spam/shadowban.
5. **Số máy bị bỏ qua an toàn (`skipped`):**
   - `follow-released-daily-cooldown`: Máy đã từng bị nhả follow ở phiên trước (Phiên 1), tự động cách ly nghỉ 24h dưỡng nick.
   - `under-6-videos-follow-disabled`: Acc chưa đủ 6 video công khai.
   - `under-21-days-follow-disabled`: Acc chưa đủ tuổi 21 ngày.
6. **Số máy chạy OK nhưng 0 lượt follow:** Quét danh sách anchor/follower khả dụng bị trống hoặc nick đích đã được follow hết từ các chu kỳ trước.

## 2. Truy Vấn Dữ Liệu Nhanh O(1)
```python
import glob, json
from collections import Counter

fl_files = glob.glob("D:/Taadaa/runtime/<cluster>/live/<date>/<run>/<timestamp>/machines/*/*/follow_result.json")
row_stats = {}
for f in fl_files:
    d = json.load(open(f, "r", encoding="utf-8"))
    r = d.get("row", "unknown")
    st = d.get("status")
    cnt = d.get("followed_count", 0)
    reason = d.get("reason", "")
    # Phân nhóm theo: success (>0), nhả follow (FOLLOW_FAILED), skipped, zero-follow
```
