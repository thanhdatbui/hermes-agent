# TikTok Comment Peek Optimization & Entropy Rules (2026-09)

## 1. Bản chất & Rủi ro khi mở comment trên video không có bình luận
- **Hiện tượng:** Video hiển thị `0` bình luận hoặc tắt tính năng bình luận nhưng script vẫn bấm mở bottom sheet comment.
- **Rủi ro telemetry/anti-bot:**
  - **Dead swipe:** Script gửi lệnh `input swipe` để cuộn lướt bên trong một View rỗng không có item. Lặp lại nhiều lần tạo tín hiệu cử chỉ bất thường (telemetry giả lập rỗng).
  - **Lãng phí thời gian phiên:** Giữ bottom sheet trống 2-4 giây vô nghĩa, giảm tốc độ và nhịp tự nhiên của phiên nuôi.
- **Nguyên tắc hành vi người thật:**
  - Khi thấy icon comment `0` hoặc không có số: Rất ít khi bấm mở (tỷ lệ tò mò < 2%).
  - Nếu lỡ mở trúng comment rỗng: Phản xạ bấm Back ngay lập tức (`0.8s - 1.2s`), tuyệt đối KHÔNG cuộn lướt.

## 2. Vấn đề pha loãng tỷ lệ thực tế (Dilution by Fast Swipe)
- Khi `session_comment_peek_rate` chỉ được tính trên các video **Deep Inspect** (`is_deep_inspect_video`):
  - Số lượng video fast swipe (lướt nhanh 1-3s không dump XML) chiếm tỷ trọng lớn trong tab For You.
  - Tỷ lệ peek config 8% - 16% trên deep inspect dẫn đến **tỷ lệ thực tế trên toàn bộ session chỉ còn 2% - 5%**, thậm chí nhiều session không mở đọc comment lần nào.
- **Quy tắc điều chỉnh:**
  - Nâng tỷ lệ peek trên deep inspect lên mức bù trừ (thường là 20% - 35% tùy session) để đảm bảo tỷ lệ tương tác đọc comment thực tế trên tổng video đạt mức tự nhiên mong muốn (~8% - 15%).

## 3. Checklist triển khai Smart Comment Peek trong flow
1. **Pre-check số comment trước khi tap:**
   - Parse `text` hoặc `content-desc` của element comment (`0`, `12`, `1.4K`, v.v.).
   - Nếu số comment == 0: **Bỏ qua (skip)**, không mở.
   - Nếu số comment > 0: Cho phép mở theo tỷ lệ `session_comment_peek_rate`.
2. **Post-check khi mở:**
   - Chỉ swipe cuộn đọc khi xác nhận có comment hiển thị.
   - Đóng sheet dứt điểm bằng phím Back, kiểm tra lại focused package TikTok ngay sau khi dismiss.
