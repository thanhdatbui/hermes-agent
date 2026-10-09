# Smart Comment Peek & Feed Comment Entropy Guidelines

## 1. Vấn đề của cơ chế Comment Peek ngây ngô (Naive Comment Peek)
- **Dead Swipe trên Popup rỗng:** Nhiều video có 0 bình luận hoặc bị chủ kênh tắt tính năng bình luận. Nếu bot vẫn bấm mở popup comment rồi thực hiện cử chỉ cuộn vuốt (`adb shell input swipe`), TikTok ghi nhận cử chỉ scroll trên một View rỗng không có item. Lặp lại nhiều lần làm giảm chất lượng telemetry của phiên nuôi acc.
- **Pha loãng tỷ lệ do Fast Swipe:** Khi `peek_rate` chỉ áp dụng trên các video `is_deep_inspect_video`, trên thực tế phần lớn video trong phiên là lướt nhanh (`fast_swipe`). Nếu đặt tỷ lệ deep inspect quá thấp (ví dụ 8% - 16%), tỷ lệ mở comment thực tế trên toàn bộ 30-50 video của phiên chỉ còn 2% - 5% (thậm chí 0 lần cả phiên), không phản ánh đúng hành vi người dùng thật.
- **Lãng phí thời gian phiên:** Mất 3–5 giây vô ích trên một video không có nội dung tương tác.

## 2. Quy chuẩn Smart Comment Peek
1. **Pre-check số lượng comment trước khi chạm (`_parse_comment_count`):**
   - Đọc `content_desc` và `text` của element comment button (và text element đếm số nằm ngay sát bên dưới ở cột phải `center[0] >= 750`, `dx <= 80`, `0 < dy <= 120`).
   - Parse chuỗi số hỗ trợ các định dạng: số nguyên (`15`), thập phân kèm đơn vị (`1.2k`, `1,5k`, `2m`), và nhãn có chữ (`Bình luận: 45`, `Bình luận 0`).
2. **Quy tắc phân nhánh hành vi:**
   - **Số comment $\le 0$ (hoặc tắt comment):** Bỏ qua hoàn toàn (`return False`), ghi log `skipped_zero_comments`, tuyệt đối không tap mở và không cuộn.
   - **Không xác định được số lượng (chỉ có icon chung chung):** Giảm tỷ lệ tò mò mở xuống còn $\le 5\%$ (`skipped_unverifiable_count`).
   - **Số comment $\ge 1$:** Cho phép mở popup theo tỷ lệ cấu hình phiên.
   - **Cử chỉ cuộn lướt:** Chỉ thực hiện `swipe` nhẹ khi chắc chắn có $\ge 5$ bình luận và trúng xác suất 50%. Nếu ít bình luận, chỉ xem tĩnh 2-3s rồi bấm Back.
3. **Cấu hình tỷ lệ động bù trừ Fast Swipe:**
   - Đặt `session_comment_peek_rate = random.randint(20, 35)` trên video deep inspect để đảm bảo trên tổng số video của toàn phiên đạt tỷ lệ tự nhiên **8% – 15%**.
4. **Đo lường & Báo cáo Telemetry Watchdog:**
   - Ghi nhận `comment_peeked` vào từng step và tổng hợp vào `action_counts["comment_peeks"]` trong metadata summary của từng máy.
   - Watchdog tổng kết Ca trích xuất `comment_peeks` từ `summary.txt` và đưa dòng thống kê vào báo cáo:
     `+ Đọc comment: {tot_comment_peeks} lượt / {tot_swipes} video ({tot_comment_rate:.1f}%)` ngay dưới dòng Thả tim.
