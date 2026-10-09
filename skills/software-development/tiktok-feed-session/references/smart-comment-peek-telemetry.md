# Smart Comment Peek & Feed Session Telemetry

## 1. Vấn đề & Rủi ro khi mở Comment bừa bãi
- **Dead Swipe (Vuốt rỗng):** Nếu video có 0 bình luận hoặc bị tắt bình luận mà script vẫn phát lệnh vuốt cuộn (`swipe`), TikTok ghi nhận hành vi bất thường trên ViewGroup rỗng, làm suy giảm chất lượng telemetry của tài khoản.
- **Pha loãng tỷ lệ thực tế:** Trong một phiên nuôi (`feed_session`), phần lớn video được lướt nhanh (`fast_swipe`). Nếu tỷ lệ mở comment chỉ tính trên video `deep_inspect` với mức thấp (8% - 16%), tỷ lệ mở thực tế trên toàn bộ phiên sẽ bị tụt xuống chỉ còn 2% - 5%, thậm chí 0%.

## 2. Quy chuẩn Smart Comment Peek (`_maybe_peek_comments`)
1. **Pre-check số lượng comment (`_parse_comment_count`):**
   - Trích xuất số lượng từ `content-desc` hoặc `text` của nút comment (hỗ trợ các định dạng: `15`, `1.2k`, `2.5m`, dấu phẩy/chấm thập phân).
   - Nếu trên icon không có số, quét element text nằm sát bên dưới icon trong cùng cột phải (`dx <= 80`, `0 < dy <= 120`).
2. **Quy tắc kích hoạt an toàn:**
   - **Comment == 0 hoặc tắt comment:** Bỏ qua hoàn toàn (`skipped_zero_comments`), không tap, không mở popup.
   - **Không xác định được số lượng (chỉ có icon chung chung):** Giới hạn tỷ lệ tò mò mở tối đa 5% (`skipped_unverifiable_count`).
   - **Comment > 0:** Cho phép mở theo tỷ lệ ngẫu nhiên của phiên.
3. **Hành vi trong Comment Sheet:**
   - Dừng đọc lướt 2.0 - 3.5 giây.
   - **Chỉ cuộn nhẹ khi có >= 5 comment** và trúng xác suất 50%. Tuyệt đối không cuộn nếu số comment ít hoặc rỗng.
   - Đóng sheet bằng phím Back (`keyevent 4`) và xác minh gói ứng dụng TikTok vẫn giữ focus.

## 3. Cân bằng Tỷ lệ Toàn phiên (Session-level Rate)
- Đặt `session_comment_peek_rate = random.randint(20, 35)` trên các video `is_deep_inspect_video`.
- Tỷ lệ này bù trừ cho các video fast swipe, giúp tỷ lệ mở comment thực tế trên tổng số video của toàn phiên đạt chuẩn người dùng thật (**~8% – 15%**).

## 4. Telemetry & Báo cáo Watchdog Cron
- **Ghi nhận Summary:**
  - `feed_swipe_smoke.py`: Đánh dấu `comment_peeked` trên từng video, tính tổng `comment_peeks` và phân phối `comment_peek_counts` theo từng tab (`for-you`, `following`, `friends`).
  - Xuất trường `"comment_peeks"` vào `summary.txt` của mỗi máy.
- **Watchdog Cron Report (`feed_session_watchdog.py`):**
  - Trích xuất `comment_peeks` từ `summary.txt`.
  - Tính tổng số lượt đọc comment và tỷ lệ phần trăm trên tổng số video lướt thành công của toàn Ca.
  - Bổ sung vào tin nhắn Telegram tổng kết Ca:
    ```text
      + Thả tim: 156 tim / 1850 video (8.4%) [Đề xuất: 120 | Bạn bè: 25 | Following: 11]
      + Đọc comment: 210 lượt / 1850 video (11.4%)
    ```
