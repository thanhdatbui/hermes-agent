# Smart Comment Peek & Telemetry Guard

## Bối Cảnh & Vấn Đề
Trong flow nuôi nick TikTok (`tiktok-luot nuoi acc`), script có hành vi mở bình luận (`_maybe_peek_comments`) để tạo tính ngẫu nhiên (entropy). Tuy nhiên:
1. **Dead Swipe trên Video Rỗng**: Nhiều video không có bình luận (hoặc bị chủ kênh tắt bình luận), script vẫn bấm mở rồi phát lệnh vuốt cuộn (`swipe`). Hành vi này tạo telemetry bất thường và lãng phí thời gian phiên nuôi.
2. **Pha Loãng Tỷ Lệ Thực Tế**: Tỷ lệ mở comment trước đây chỉ cấu hình 8% - 16% trên các video deep-inspect (dump XML). Do phần lớn video trong feed là lướt nhanh (fast swipe), tỷ lệ mở comment thực tế trên toàn bộ session bị kéo tụt xuống chỉ còn 2% - 5%, quá thấp so với người dùng thật.

---

## Cơ Chế Khắc Phục Chuẩn (Commit `5854e4e`)

### 1. Pre-Check Số Lượng Bình Luận (`_parse_comment_count`)
- Bóc tách số lượng từ `content_desc` hoặc `text` của button comment (hoặc label text ngay bên dưới nút).
- Regex nhận diện đa ngôn ngữ:
  - Chuẩn quốc tế: `123`, `1.2k`, `1,5k`, `2m`.
  - Chuẩn tiếng Việt: `500 n`, `2 tr`.
- **Fail-Closed Zero-Comment Guard**:
  - Nếu `comment_count is None` hoặc `comment_count <= 0`: Bỏ qua ngay lập tức (`return False`), ghi log `skipped_zero_comments` hoặc `skipped_unverifiable_comments`. Tuyệt đối không bấm nút mở panel.

### 2. Cuộn Có Điều Kiện & Closed-Loop Verification
- Chỉ thực hiện cuộn nhẹ (`swipe`) khi xác nhận video có từ **5 bình luận trở lên** (`comment_count >= 5`) với xác suất 50%.
- Sau khi bấm phím Back (`keyevent 4`) để đóng comment sheet, bắt buộc chạy **Closed-Loop Verification**:
  - Kiểm tra `focused_package` vẫn thuộc TikTok (`trill`, `musically`, `aweme`).
  - Nếu app bị văng hoặc lệch focus, fail-closed và ghi nhận lỗi dismiss.

### 3. Điều Chỉnh Tỷ Lệ Phiên (Session Rate)
- Tỷ lệ ngẫu nhiên của phiên trên video deep inspect được nâng lên:
  ```python
  session_comment_peek_rate = random.randint(20, 35) if is_feed_session else 25
  ```
- Nhờ đó, bù trừ cho các video fast swipe, tỷ lệ mở đọc comment thực tế trên toàn ca đạt chuẩn tự nhiên từ **8% – 15% tổng số video**.

### 4. Tích Hợp Telemetry Vào Watchdog Báo Cáo Ca Telegram
- Ghi nhận `comment_peeked: bool` vào `summary.txt` từng video và tổng hợp vào `comment_peeks` metadata.
- Script `feed_session_watchdog.py` tự động bóc tách số liệu và format vào tin nhắn báo cáo ca:
  ```text
  • Lướt Feed:
    + Thả tim: 156 tim / 1850 video (8.4%) [Đề xuất: 120 | Bạn bè: 25 | Following: 11]
    + Đọc comment: 210 lượt / 1850 video (11.4%)
  ```
