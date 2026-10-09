# Case 180: Bóc Tách Tỉ Lệ Thả Tim Tab Bạn Bè / Following Bất Thường Trên Báo Cáo Watchdog

## 1. Hiện Tượng & Băn Khoăn Vận Hành
- Báo cáo Watchdog báo: `Thả tim: 133 tim / 1185 video (11.2%) [Đề xuất: 126 (31.5%) | Bạn bè: 2 (8.7%) | Following: 5 (50.0%)]`.
- Người vận hành thắc mắc: "Mày có thấy báo cáo có 8% k?" do tỉ lệ tim tab Bạn bè chỉ đạt 8.7%, trong khi cấu hình danh nghĩa là 35% - 50%.

## 2. Quy Trình Điều Tra O(1) Không Cần Scan Đĩa
Để giải thích chính xác con số mà không đoán mò:
1. Xác định run directory của ca tương ứng trong `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<R>-<time>/<run_id>/`.
2. Kiểm tra `machines/*/*/summary.txt`:
   - Dữ liệu tóm tắt `details.json` lưu trữ cấu trúc `feed_counts` và `like_counts` của từng máy.
3. Chạy script một dòng trích xuất thống kê tổng hợp `feed_counts["friends"]` vs `like_counts["friends"]` trên toàn bộ các máy.

## 3. Bản Chất Số Học & Cơ Chế Hoạt Động
1. **Mẫu số cực nhỏ (Small Sample Size Bias):**
   - Không phải toàn bộ 1.185 video đều là video Bạn bè.
   - Do feed distribution phân bổ phần lớn cho For You (70-80%), toàn ca 80 máy chỉ có 15 máy có lượt chuyển sang tab Bạn bè ở nhịp Deep Inspect.
   - Tổng số video Deep Inspect ở tab Bạn bè trên toàn farm chỉ vỏn vẹn **26 video**.
2. **Kẹt màn hình gợi ý / Empty Suggestion Feed:**
   - 31/80 máy khi chuyển sang Bạn bè gặp popup hoặc màn hình gợi ý (`contact_follow_suggestion`, `follow_friends_suggestion_popup`, "Hãy follow bạn bè...").
   - Các máy này không có video player thật -> không thể xuất hiện nút Like -> trả về 0 tim.
3. **Xác suất xúc xắc (Dice Roll Variance):**
   - Với các máy gặp 1-2 video Bạn bè thật, xác suất 35-45% khi tung xúc xắc cho 1-2 lần rất dễ rơi vào cửa trượt (roll > rate), dẫn đến 0 tim.
   - Trong phiên này, chỉ có duy nhất **Máy 44** trúng xúc xắc và thả 2 tim / 2 video (100% trên máy đó).
   - Tổng kết: `2 tim / 26 video deep inspect = 7.7%` (watchdog lọc theo các máy success ra 8.7%).

## 4. Kết Luận Vận Hành
- Tỉ lệ 8.7% không phải do lỗi script hay bot bị chặn Like, mà là hệ quả tự nhiên của việc **mẫu số video bạn bè quá ít (26 video)** kết hợp với **phần lớn nick bị rỗng bạn bè / kẹt màn hình gợi ý**.
