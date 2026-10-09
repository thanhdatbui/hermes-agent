# TikTok Feed Session: Rewind Swipe & Independent Bookmark

## 1. Rewind Swipe (Vuốt ngược xem lại video trước)
- **Mục tiêu**: Giả lập hành vi người dùng lướt lố qua video hay, vuốt ngược xuống dưới để xem lại nhằm tạo Session Narrative tự nhiên, phá vỡ nhịp vuốt 1 chiều đơn điệu.
- **Quy tắc thực hiện**:
  - Tỷ lệ: 5% - 8% (thường dùng `random.randint(1, 100) <= 6`).
  - Điều kiện: Chỉ áp dụng khi `swipe_count >= 3` và không phải video cuối cùng (`not is_last_video`).
  - Hướng swipe: Vuốt từ trên xuống dưới (`start_y = 480`, `end_y = 1380`, `start_x, end_x` trong hành lang an toàn [450, 540]).
  - Invariant clamp: Hàm chuẩn hóa swipe phải cho phép `start_y < end_y` (chỉ chặn khi `start[1] == end[1]`).
  - Dwell time: Sau khi vuốt ngược, dừng xem video cũ 2 - 4 giây trước khi tiếp tục chu kỳ feed tiếp theo.

## 2. Independent Bookmark (Lưu video độc lập không cần Like)
- **Mục tiêu**: Phá vỡ tương quan cứng `Like -> Save` (vốn là dấu hiệu bot dễ bị TikTok phát hiện nếu 100% bookmark đều đi kèm like).
- **Quy tắc thực hiện**:
  - Tỷ lệ: 3% - 5% (mặc định `rate_percent = 4`).
  - Điều kiện: Kích hoạt khi video **không** được thả tim (like roll fail, nút like đã like từ trước, hoặc nút like không tìm thấy).
  - Tương tác: Bấm trực tiếp vào tọa độ center của nút Bookmark (`UIElement` Bookmark) qua `input tap x y`, delay nhẹ 0.4 - 0.8s.
