# In-Feed Natural Follow & Watch Time Gate Architecture (2026-09-23)

## 1. Bối cảnh & Hiện tượng Silent Action Block (Nhả Follow)

Trên hệ thống Phone Farm Android (Samsung S7), khi kích hoạt tính năng tự động bấm follow tài khoản trong lúc lướt For You feed, nhiều tài khoản gặp hiện tượng:
- Sau khi ADB tap vào nút "Follow / Theo dõi", nút chuyển trạng thái "Đang follow / Following".
- Nhưng chỉ sau 2-3 giây (hoặc khi vuốt sang video kế tiếp), nút follow bị TikTok revert đỏ trở lại, hoặc số `Following` trên profile không hề tăng.
- **Nguyên nhân cốt lõi**: Bot vừa quẹt tới video đã tap nút Follow ngay (< 2-3 giây sau khi dừng màn hình). Hệ thống AI chống bot của TikTok phát hiện tốc độ tương tác bất thường (không có thời gian xem/nghiền ngẫm nội dung), lập tức kích hoạt cơ chế **Silent Action Block** để âm thầm drop action mà không cần thông báo lỗi ra UI.

---

## 2. Phân tách Kiến trúc 2 Tầng Follow của Farm

Hệ thống Taadaa Farm phân định rõ 2 tầng tương tác follow độc lập:

| Đặc tính | Tầng 1: Cross-Farm Follow Runner (`follow_runner.run_follow`) | Tầng 2: Follow Tự Nhiên Trong Feed (`feed_swipe_smoke.py`) |
| :--- | :--- | :--- |
| **Vị trí thực thi** | Chạy sau khi kết thúc phiên lướt feed (`_run_follow_hook` trong `multi_machine_feed_session.py`). | Chạy xen kẽ ngay trong vòng lặp lướt video (`_maybe_follow_video`). |
| **Chế độ hoạt động** | Mode 1 (Search từ khóa ➔ Follow) / Mode 2 (Anchor profile ➔ Follow followers). | Tìm nút Follow xuất hiện trực tiếp trên màn hình xem video. |
| **Cổng an toàn (Gate)** | Bắt buộc `video_count >= 10`. Nick clone/trắng dưới 10 video tuyệt đối bị SKIP (`under-10-videos-follow-disabled`) để tránh lộ cụm farm chéo. | KHÔNG dùng cổng 10 video. Phục vụ mồi tệp sở thích (seeding) tự nhiên cho nick từ giai đoạn mới reg/ngâm. |
| **Tần suất** | Theo cấu hình batch (thường 5 - 15 follows/lần chạy). | Tỷ lệ ngẫu nhiên thấp: For You 5%, Deep Inspect 20% (trung bình ~1 - 2 follow/phiên). |

---

## 3. Quy chuẩn Watch Time Gate (Chống Nhả Follow)

Trong `feed_swipe_smoke.py` tại hàm `_maybe_follow_video(ctx, after_attempt, follow_rate_percent)`:
- Sau khi kiểm tra tỷ lệ ngẫu nhiên `random.randint(1, 100) > int(follow_rate_percent)`:
- **BẮT BUỘC** thực hiện **Watch Time Gate**:
  ```python
  # Watch Time Gate (Chống nhả follow): Ngâm video tối thiểu 8-12s trước khi tương tác follow
  # Đảm bảo TikTok ghi nhận watch-time đủ độ trust, tránh hành vi bot bấm vội bị server revert
  watch_dwell_s = random.uniform(8.0, 12.0)
  time.sleep(watch_dwell_s)

  xml_text = _capture_xml_text(ctx, "follow_video")
  ```
- **Hiệu ứng**: Khi video được xem liên tục 8 – 12 giây trước khi bấm nút, server TikTok ghi nhận session có high retention / completion time thực tế, độ trust của hành động follow đạt mức cao nhất và không bị hệ thống kiểm duyệt hủy ngầm.

---

## 4. Telemetry & Báo cáo Giám sát Ca (`feed_session_watchdog.py`)

Dữ liệu follow tự nhiên được trích xuất và hiển thị độc lập với follow chéo:
1. **Trích xuất**: `parse_run_all` đọc trường `follow_counts` từ `summary.txt` của từng máy, lưu vào trường `natural_follows` trong `m_payload`.
2. **Hợp nhất (Merge)**: `merge_machine_result` lấy max số follow tự nhiên theo từng feed type (`for-you`, `following`, `friends`).
3. **Hiển thị báo cáo Telegram**:
   Được chèn ngay dưới dòng Thả tim trong block `🏢 【FARM ...】`:
   ```text
   • Lướt Feed:
     + Success (78): 1, 2, 3...
     + Thả tim: 142 tim / 1520 video (9.3%) [Đề xuất: 98 (8.5%) | Bạn bè: 44 (12.1%) | Following: 0 (0.0%)]
     + Follow tự nhiên: 24 lượt / 1520 video (1.6%) [Đề xuất: 18 | Bạn bè: 6]
     + Đọc comment: 380 lượt / 1520 video (25.0%)
   ```

---

## 5. Quy hoạch Slot Dàn Kênh Chuyển Đổi (Visual / Niche Mới)

Khi cần chọn tài khoản để xây dựng tệp kênh mới (ví dụ: Niche Visual / Gái xinh Douyin):
- **Nguyên tắc**: Tuyệt đối không can thiệp vào các Tik slot đã định vị ổn định lâu năm (`Tik1`, `Tik2` với trung bình 10 – 21 video/acc).
- **Kho chuyển đổi lý tưởng**:
  - `Tik7.xlsx`: Có tới 38 nick chưa từng đăng video (0 video) và 34 nick chỉ đăng 1 clip.
  - `Tik5.xlsx`: Có 17 nick 0 video và 53 nick đăng ít (< 3 clip).
- Khi chuyển đổi: Cập nhật niche trong `data/niches_pool.txt`, cấp nguồn video sạch (1080p không logo từ Douyin qua `download_douyin_visual.py`), bật Follow tự nhiên kèm Watch Time Gate để mồi tệp thuật toán FYP.
