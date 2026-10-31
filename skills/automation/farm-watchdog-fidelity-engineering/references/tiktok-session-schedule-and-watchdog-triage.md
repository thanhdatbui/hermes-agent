# TikTok Session Schedule & Watchdog Triage Playbook

## 1. Farm Schedule Parity (3 Ca x 2 Phiên / ngày)
Hệ thống TikTok Phone Farm (Kibe 1-80 & Admin 201-280) hoạt động theo chu kỳ 4 ngày, mỗi ngày gồm 3 Ca x 2 Phiên:
- **Ca 1 (Sáng):**
  - Phiên 1: **06:00** (thường hoàn tất ~07:30 - 07:45)
  - Phiên 2: **08:00** (thường hoàn tất ~08:45 - 08:55; kèm Follow chéo + Upload video)
- **Khung nghỉ sáng (09:00 - 12:00):**
  - Farm rảnh, hoàn toàn **KHÔNG có phiên nuôi feed/follow chạy**.
  - Dành riêng cho watchdog nền: GPM Gmail Login, Gmail 2FA, Avatar upload.
- **Ca 2 (Trưa):** Phiên 1 (**12:00**), Phiên 2 (**14:00**).
- **Khung nghỉ chiều (15:00 - 18:00):** Tương tự, không chạy feed/follow.
- **Ca 3 (Tối):** Phiên 1 (**18:00**), Phiên 2 (**20:00**).

## 2. Kênh Định Tuyến Báo Cáo Telegram
Báo cáo tự động từ Hermes Cron không gửi về User DM mà định tuyến về các nhóm chuyên biệt:
- **Nuôi Feed:** Bắn về nhóm `Tiktok Luot Nuoi Acc` (`telegram:-5377611430`).
- **Follow chéo:** Bắn về nhóm `Tiktok Follow` (`telegram:-5127276494`).

## 3. Quy Trình Điều Tra Nhanh Khi Thiếu Báo Cáo (O(1) Audit)
Khi User hỏi tại sao không có báo cáo ở mốc giờ bất thường (ví dụ ~10:45 sáng):
1. **Kiểm tra State Files:**
   - `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`
   - `D:/Taadaa/runtime/kibe/cron-state/follow_session_reported.json`
   - Kiểm tra xem session key (ví dụ `YYYY-MM-DD_ca1_phien2`) đã nằm trong `reported_sessions` chưa và mtime của file.
2. **Kiểm tra SQLite Sổ Cái (`session_action_stats`):**
   - Truy vấn `SELECT * FROM session_action_stats WHERE session_key LIKE 'YYYY-MM-DD%'` trong `D:/Taadaa/data/tiktok_tracker.db`.
   - Xác nhận số liệu thực tế: `internal_fl`, `natural_fl`, `likes`, `swipes`, và timestamp chốt sổ.
3. **Phân biệt Lịch Chạy vs Lỗi Hệ Thống:**
   - Nếu thời điểm rơi vào khung nghỉ (09:00 - 12:00, 15:00 - 18:00), xác nhận ngay với User rằng ca trước đã xong, phiên tiếp theo sẽ chạy đúng giờ quy định (12:00, 18:00).
   - Trích xuất và tóm tắt ngay số liệu thực tế của các phiên đã chạy để trả lời trực tiếp trong chat.
4. **Lưu ý Va Chạm Tiến Trình (`runner_busy`):**
   - Trong `feed_session_watchdog.py`, `is_feed_runner_active()` kiểm tra cả `tiktok_workflow` và `tiktok_upload`. Các tiến trình upload avatar chạy trong khung rảnh có thể kích hoạt cờ `runner_busy=True`, khiến watchdog giữ trạng thái chờ nếu phiên chưa chốt trước đó.
