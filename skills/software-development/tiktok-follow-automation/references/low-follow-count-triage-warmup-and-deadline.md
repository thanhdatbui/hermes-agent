# Chẩn đoán nguyên nhân Follow thấp (1–5 lượt) & Cơ chế Dưỡng sinh Ngẫu nhiên

Khi báo cáo watchdog ghi nhận các máy đạt 1–5 lượt follow và được xếp vào nhóm **Success (OK)** thay vì hạn mức danh nghĩa 10–20 lượt, kiểm tra 3 nguyên nhân cốt lõi sau:

---

## 1. Hạn mức Dưỡng sinh / Thăm dò sau mãn hạn Cooldown (`is_post_cooldown_warmup`)
- **Cơ chế:** Khi tài khoản từng dính án phạt nhả follow (`fail_streak > 0`) và vừa hết hạn cooldown (`not follow_failed`), hệ thống kích hoạt chế độ **Warm-up**.
- **Hạn mức phiên:** Tự động bị giới hạn cứng tại `random.randint(3, 5)` lượt follow/phiên (thay vì 10–20 lượt) để bảo vệ acc không bị TikTok quét lại ngay sau khi mở chặn.
- **Dấu hiệu:** `status: OK`, `follow_failed: false`, `budget_used` đạt từ 3 đến 5 lượt. Đây là hành vi hoàn thành 100% chỉ tiêu thiết kế, không phải lỗi.
- **Xác minh O(1):** Đọc file state `runs/state/follow_state_<M>_row_<R>.json`, kiểm tra `fail_streak > 0` và `cooldown_expiry` vừa qua.

---

## 2. Safety Deadline Gate bỏ qua Module 1 bù (`has_time_for_next_action`)
- **Cơ chế:** Trong chế độ hybrid (`mode: "both"`), Mode 2 (Anchor Following) chạy trước, Mode 1 (Search-Follow) chạy sau để bù nếu chưa đủ budget.
- **Chốt chặn an toàn:** Code kiểm tra thời gian session còn lại trước khi kích hoạt Mode 1:
  ```python
  if not self.has_time_for_next_action(reserve_seconds=180.0):
      logger.info("Session deadline approaching, skipping mode1 after mode2 with %d followed accounts", len(res.followed))
  ```
- **Hành vi:** Mode 2 thường ngốn 17–18.5 phút (do vào profile, mở tab, cuộn lọc nick, giữ delay an toàn giữa các nhịp tap). Khi hoàn tất Mode 2, thời gian còn lại của budget 20 phút (1200s) thường chỉ còn 100–160s (< 180s).
- **Kết quả:** Script chủ động bỏ qua Mode 1 và chốt kết quả tại chỗ (`status: OK`, `mode2_followed_count > 0`, `mode1_followed_count: 0`) để tránh bị watchdog trảm giữa chừng gây treo màn hình hoặc hỏng trạng thái app.

---

## 3. Cạn nick nội bộ chưa follow trong tệp Anchor (Duplicate Skip Streak)
- **Cơ chế:** Mode 2 chỉ follow các nick nội bộ nằm trong tệp farm (`internal_uids`).
- **Hành vi:** Nếu acc đã follow hầu hết các nick trong danh sách của 3 Anchor ngẫu nhiên từ các phiên trước, các hàng tiếp theo đều rơi vào trạng thái `"đã follow sẵn (skip)"`.
- Khi cuộn liên tiếp 5 lần mà không tìm thấy nick nội bộ mới (`idle_scrolls >= 5`), script ngắt vòng lặp an toàn và trả về số lượt đã follow thực tế.

---

## 4. Cơ chế Dưỡng sinh Ngẫu nhiên Từng Nick (Per-Account Organic Rest 1/3)

Thay thế chu kỳ Modulo 6 toàn farm cũ (tránh việc cả đàn 80 máy cùng nghỉ/cày đồng loạt gây pattern bot cluster trên proxy):
- **Phép toán xác suất chuẩn:** Trong Modulo 6 cũ, mỗi nick cày 2 ngày và nghỉ 1 ngày dưỡng sinh trong mỗi 3 ngày được bật máy. Do đó, tỷ lệ ngày dưỡng sinh chính xác là **1/3 (~33.33%)**.
- **Công thức phân bổ độc lập:**
  ```python
  h = hashlib.md5(f"{date_str}:{machine}:{row}".encode("utf-8")).hexdigest()
  is_rest_day = (int(h[:8], 16) % 3) == 0  # 1/3 xác suất
  ```
- **Hành vi ngày Dưỡng Sinh (`is_rest_day == True`):**
  - **Follow Hook:** Safe-skip với reason `organic-rest-day-pure-feed` (0 follow).
  - **Upload Hook:** Safe-skip với reason `organic-rest-day-no-upload` (0 upload).
  - **Chỉ lướt Feed (Pure Feed):** Đóng vai trò consumer xem video tự nhiên giúp làm sạch trust score và giảm tải hệ thống.
