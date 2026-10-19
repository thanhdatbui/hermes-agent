# Phantom Follow State Reconciliation & Rest-Day Weak Account Allocation

## 1. Dữ liệu Following Ảo (Phantom Followed State Reconcile)
- **Bối cảnh lịch sử**: Trước đợt fix verify ngày 01/10/2026, `follow_runner` chưa kiểm tra reload nút follow triệt để. Khi bấm vào nút follow, nếu TikTok âm thầm từ chối (Silent Drop) hoặc nhả sau vuốt, script cũ vẫn ghi nhận UID đó vào từ điển `followed` trong `follow_state_<machine>_row_<row>.json`.
- **Hậu quả**:
  * State JSON ghi nhận số lượng follow lớn hơn rất nhiều so với thực tế trên TikTok Web (ví dụ: M27 ghi nhận 115 lượt trong khi Web chỉ có 43 lượt, dư 72 lượt phantom).
  * Làm cháy tệp target: Nick lọc qua `state.is_followed(uid)` thấy hầu hết target nội bộ đều đã đánh dấu follow rồi, dẫn đến không còn đối tượng để follow hoặc bị ép tìm anchor lạ.
  * Gây ngộ nhận phân loại Cohort: Nick non bị tính nhầm thành Veteran do `len(followed) >= 100`, dẫn đến cấp quota quá tải làm chết nick.
- **Quy trình Reconcile chuẩn**:
  1. Đọc số lượng following thực tế từ snapshot Web (`snapshots` table trong `tiktok_tracker.db`).
  2. Đối soát danh sách UID trong state JSON với ngày ghi nhận trước 2026-10-01.
  3. Dọn dẹp cờ phantom: Chỉ giữ lại các UID thực sự được TikTok công nhận; giải phóng các UID ảo để trả lại tệp target sạch cho nick.

## 2. Dynamic Weak Picker — Khắc Phục Lỗi Thiên Kiến Hàng (Row Blindness)
- **Vấn đề**: Trong chu kỳ 4 ngày, ca tối Ngày 3 và 3 ca Ngày 4 được dành cho nuôi nick yếu / ăn nhả. Tuy nhiên, logic cũ thường mặc định Row 1 và Row 2 là "hàng cựu binh khỏe" và chỉ bốc nick ở Row 7, Row 8, khiến các nick dính án tù đọng (`fail_streak >= 2`) ở Row 1, Row 2 bị bỏ đói nhịp tương tác dưỡng sinh.
- **Quy tắc điều phối bắt buộc**:
  * `Vulnerability Score` phải chấm điểm độc lập trên từng slot (1 đến 8) của mỗi máy, **tuyệt đối không phân biệt Row**.
  * Nick có `fail_streak >= 2` hoặc đang dính Follow Cooldown phải được gán trọng số ưu tiên cao nhất ($P = 1.0$), tự động được bốc vào lướt feed trong ca tối N3 và các ca N4 để xả tải và tích lũy độ uy tín.

## 3. Bảng Cooldown Phạt Follow Chuẩn Hóa Theo Streak
Quy định thời gian cách ly cứng trong `follow_state.py` (tuyệt đối không nhầm lẫn):
- `Streak = 1`: Cooldown **3 ngày**.
- `Streak = 2`: Cooldown **5 ngày**.
- `Streak = 3`: Cooldown **7 ngày** (1 tuần).
- `Streak >= 4`: Cooldown **15 ngày** (nửa tháng).

## 4. Kỷ Luật Vận Hành & Bảo Toàn Tài Sản Nick Farm
- **Bác bỏ định kiến**: Acc trước khi vào follow hook đều đã hoàn thành feed session đầy đủ trong `multi_machine_feed_session.py`. Lỗi nhả nút là do TikTok Action Block tầng Write, không phải do nick chưa xem feed.
- **Cấm đóng băng tài sản**: Tuyệt đối không đề xuất "đóng băng vĩnh viễn" các nick có tuổi, có video và đang LIVE. Nick ăn nhả vẫn được duy trì lướt feed và upload video 1 clip/ngày đều đặn; khi ra tù chỉ cấp 1-2 follow dò đường an toàn.
