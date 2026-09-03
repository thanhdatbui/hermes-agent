# Chẩn Đoán Nhả Follow (Follow Drop) & Đối Soát Lịch Sử Theo Chu Kỳ Ca Chẵn/Lẻ

## 1. Bối Cảnh & Phân Tích Lỗi Nhả Follow (Follow Drop / Rollback)

Khi runner follow thực hiện thao tác follow một tài khoản (anchor hoặc follower target) qua Path B / Mode 2:
1. **Kiểm tra trạng thái sau vuốt:** Runner thực hiện tap Follow, sau đó vuốt nhẹ / refresh profile và kiểm tra lại nút quan hệ.
2. **Hiện tượng "Nhả Follow":** Nút chuyển về trạng thái chưa follow (`Follow` thay vì `Đang follow` / `Following` / `Bạn bè`), runner phân loại `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session` và kích hoạt cooldown cho tài khoản đó trong ngày để bảo vệ nick.

### Phân Loại Mức Độ Nhả Follow
- **Nhả ngay lượt đầu (`followed_count = 0`):** Tài khoản bị shadow drop / rate-limit cấp độ tài khoản ngay từ đầu phiên, hoặc anchor UID bị gắn cờ hạn chế tương tác.
- **Nhả sau một số lượt (`followed_count = 1..16`):** Tài khoản đã hoàn thành thành công $N$ lượt follow trước khi chạm giới hạn tần suất (rate-limit) của TikTok trong phiên hiện tại.

---

## 2. Quy Trình Trích Xuất Dữ Liệu Thực Tế Khi Điều Tra

Khi người dùng hỏi về tình trạng nhả follow của các máy:
1. **Đọc trực tiếp thư mục runtime của phiên hiện tại:**
   - Đường dẫn: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\<shift-folder>\<run-id>\machines\machine_<N>\<run-id>\follow_result.json`.
   - Trích xuất: `status`, `followed_count`, `details` / `reason`, anchor UID gây dừng phiên.
2. **CẤM quét đệ quy toàn bộ thư mục runtime:** Luôn truy cập trực tiếp theo số máy `machine_<N>` đã biết để tránh nghẽn I/O.
3. **Báo cáo rõ ràng 2 thông số:**
   - Số lượng follow đã hoàn thành trước khi dừng.
   - Nguyên nhân dừng cụ thể (nhả anchor nào, không nhận follow ở profile nào).

---

## 3. Quy Tắc Đối Soát Lịch Sử Chu Kỳ Ca Chẵn / Lẻ (Odd / Even Schedules)

Hệ thống phân bổ tài khoản theo quy tắc:
- **1 Máy = 3 Ca = 6 Row:**
  - Ca 1 (Sáng): Row 1 (Ngày Lẻ) / Row 2 (Ngày Chẵn).
  - Ca 2 (Trưa/Chiều): Row 3 (Ngày Lẻ) / Row 4 (Ngày Chẵn).
  - Ca 3 (Tối): Row 5 (Ngày Lẻ) / Row 6 (Ngày Chẵn).
- **Lịch Ngày Chẵn (2, 4, 6):** Chạy Row 2, Row 4, Row 6.
- **Lịch Ngày Lẻ (1, 3, 5, 7):** Chạy Row 1, Row 3, Row 5.

### Lưu Ý Quan Trọng Khi Truy Vết Lịch Sử Của Một Row
- Khi kiểm tra lịch sử "2 ngày trước" của một tài khoản trên **Row 2**:
  - Không đọc dữ liệu của ngày hôm qua (ngày lẻ, chạy Row 1/3/5).
  - Phải lùi về đúng ngày Chẵn gần nhất trước đó (ví dụ: ngày 02/09 -> kiểm tra ngày 30/08).
- Tránh kết luận nhầm "tài khoản không chạy" khi ngày hôm trước là ngày nghỉ theo chu kỳ của Row đó.

---

## 4. Cơ Chế Báo Cáo Của Feed Session Watchdog & Độ Trễ Thời Gian

- Script `feed_session_watchdog.py` chạy theo chu kỳ cron `*/5 * * * *` (mỗi 5 phút).
- Watchdog tuân thủ nguyên tắc **Silent Watchdog**: Chỉ gửi báo cáo khi phát hiện phiên ĐÃ HOÀN TẤT (`run_manifest.json` có `end_time` và `completed_steps`).
- **Trường hợp phiên kết thúc lệch giây so với tick cron:**
  - Ví dụ: Phiên kết thúc lúc `06:45:46`, lượt cron lúc `06:45:22` kiểm tra thấy phiên chưa xong nên im lặng.
  - Watchdog sẽ gửi thông báo vào lượt cron tiếp theo lúc `06:50:00`.
  - Đây là cơ chế vận hành bình thường, không phải lỗi sót báo cáo.
