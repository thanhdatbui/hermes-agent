# Cơ chế chọn Anchor và Cuộn sâu danh sách Following trong Mode 2

## 1. Bản chất & Quy tắc chọn Anchor
- **Không phân biệt trạng thái follow của Anchor:** Anchor đã follow hay chưa follow đều hợp lệ để mở danh sách Following. Tránh tình trạng loại bỏ anchor đã follow khiến cạn kiệt nguồn anchor xịn. Cơ chế lọc `is_followed` CHỈ áp dụng cho các tài khoản con bên trong danh sách, không áp dụng cho anchor mẹ.
- **Ngưỡng lọc sàn Anchor dày:** Chỉ bốc các Anchor có `following >= 150` (dựa trên snapshot mới nhất trong `tiktok_tracker.db`), tránh bốc nhầm các anchor mỏng mới nuôi chưa có nhiều nick nội bộ.

## 2. Kỹ thuật cuộn sâu và chống dừng sớm (Deep Scroll Safeguards)
- **Rủi ro bẫy `idle_scrolls` thấp:** Khi một tài khoản đã follow 20-30 nick của anchor từ các phiên trước, các nick này sẽ nằm ở đầu danh sách. Nếu để `idle_scrolls >= 5` thì chỉ sau ~25 nick đã follow, bot sẽ tưởng nhầm là hết nick và ngắt sớm, bỏ lỡ hàng trăm nick bên dưới.
- **Rủi ro trần `max_scrolls` thấp:** Anchor 300-400 following cần 60-80 lần vuốt. Giới hạn `max_scrolls = 40` sẽ cắt cụt nửa sau danh sách.
- **Cơ chế chuẩn hóa:**
  1. Nâng trần `max_scrolls` lên tối thiểu 90-100 lần vuốt.
  2. Bắt buộc dùng cơ chế phát hiện chạm đáy thật (True Bottom Detection) qua `seen_handles`: chừng nào sau mỗi lượt vuốt vẫn xuất hiện handle mới trên RecyclerView thì bot vẫn tiếp tục cuộn tìm nick farm nội bộ.
  3. Chỉ dừng khi thỏa mãn 1 trong các điều kiện:
     - Đã đạt đủ session budget (`used >= budget`).
     - Chạm đáy thật của danh sách (không phát hiện thêm handle mới sau 3 lần vuốt liên tiếp).
     - Chạm trần an toàn `max_scrolls`.
     - Hết thời gian phiên (`has_time_for_next_action() == False`).
