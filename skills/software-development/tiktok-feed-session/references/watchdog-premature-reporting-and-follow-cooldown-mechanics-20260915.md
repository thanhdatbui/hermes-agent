# Pitfall & Recovery: Watchdog Premature Reporting vs Follow State Mechanics (2026-09-15)

## 1. Race Condition: Watchdog Premature Reporting (0 Lượt Follow ảo)

### Triệu chứng:
Báo cáo Telegram từ `feed_session_watchdog.py` báo:
- Follow chéo (0 lượt follow).
- Lỗi script/xác minh (70 máy).
Nhưng kiểm tra thực tế runtime `follow_result.json` thì có 10-14 máy follow thành công, tổng cộng 56-88 lượt follow.

### Root Cause:
1. `can_report_session()` kiểm tra `completed_expected_count >= expected_count` (đã đủ 80 máy xong khâu lướt Feed).
2. Điều kiện này được đặt trước kiểm tra `if runner_busy: return False`, dẫn tới việc watchdog chốt báo cáo ngay tại thời điểm Feed vừa xong (06:56:10), trong khi các worker thread vẫn đang bận chạy follow hook và ghi `follow_result.json` (máy cuối cùng đến 07:00:29 mới flush xong).
3. Do tập `all_follows` chưa kịp đọc dữ liệu, watchdog rơi vào nhánh fallback: máy nào có status lướt Feed là `success` mà chưa có kết quả follow thì gán vào `fl_error` (Lỗi script/xác minh).

### Giải pháp Invariant:
- Trong khung giờ của ca/phiên, **tuyệt đối không chốt báo cáo nếu `runner_busy == True`**, bất kể đã đủ số máy hoàn tất Feed.
- Bắt buộc phải đợi runner hoàn tất toàn bộ chu trình (bao gồm Follow hook và Upload hook) hoặc đợi hết Grace Period mới được chốt báo cáo.

---

## 2. Bản chất Cơ chế State Machine Cooldown Follow (`follow_state`)

### Thắc mắc của User:
"Máy follow được là máy chưa từng bị nhả hay sao?"

### Bản chất kỹ thuật:
- **KHÔNG PHẢI**: Máy follow được không phải là máy chưa từng bị TikTok nhả follow.
- Mỗi máy/slot tài khoản có 1 file state độc lập: `follow_state_{machine}_row_{account_row_index}.json`.
- Hệ thống quản lý theo cơ chế **`fail_streak`**:
  * Khi bị TikTok nhả follow (`FOLLOW_FAILED` sau khi re-verify profile): tăng `fail_streak`, áp dụng án phạt cooldown:
    - `streak = 1`: Cooldown đến 23:59:59 của ngày hôm đó (daily cooldown).
    - `streak = 2`: Cooldown 4 ngày.
    - `streak >= 3`: Cooldown 7 ngày.
  * Khi hết hạn cooldown (`cooldown_until_at < now_utc`), trạng thái tự động mở lại (`follow_failed = False`), chuyển sang pha Warmup sau cooldown (`is_post_cooldown_warmup`).
  * Khi follow thành công và verified trên profile: reset `fail_streak = 0`, xóa bỏ toàn bộ dấu vết cooldown.
- Các máy follow được trong phiên (ví dụ M4, M20, M26...) tại Row 1 đều đã từng có lịch sử bị phạt ở các row/thời điểm khác, nhưng ở Row 1 hiện tại đã mãn hạn phạt (`fail_streak = 0`) và TikTok chấp nhận lượt follow thật 100%.

---

## 3. Lỗi Account Switcher do lệch Display Name vs Username

### Triệu chứng:
Máy báo lỗi `manual-needed:account-switcher-missing-expected: expected account not found in account switcher` (ví dụ M14, M41, M50, M71).

### Nguyên nhân:
- TikTok trên một số thiết bị hiển thị dòng tài khoản trong Switcher sheet bằng **Display Name (Tên hiển thị)** thay vì Username (`@username`).
- Ví dụ:
  * Workbook ghi ID là `hong.bo.anh83`, nhưng UI switcher chỉ hiển thị text `Anh Hoang`.
  * Workbook ghi ID là `thu.trangg584`, nhưng UI switcher hiển thị `Trang Le`.
  * Workbook ghi ID là `hng.th.v713`, nhưng UI switcher hiển thị `Hong Vu`.
- Do parser chỉ tìm kiếm theo `expected_account` (username), không khớp được với TextView hiển thị display name nên đánh giá nhầm là thiếu nick.

### Hướng xử lý:
- Trong `feed_swipe_smoke.py`, cơ chế `_find_account_switch_option` và `find_exact_account` cần đối chiếu thêm qua mapping alias (Display Name ↔ Username) được sync từ workbook hoặc lịch sử nhận diện profile trước đó.
