# Unjust Streak Inflation, False Failure Accounting & Cooldown Reconciliation

## 1. Nguyên Tắc Cốt Lõi Về Phạt Fail Streak
- **Chỉ tính streak tăng khi và chỉ khi:** Tài khoản thực sự ra sân chạy, bấm follow phát đầu tiên nhưng bị TikTok nhả nút ngay lập tức (`fl = 0`, `follow_failed = True`) qua N chu kỳ liên tiếp.
- **CẤM TUYỆT ĐỐI tăng streak khi:**
  1. **Lỗi mạng / Sập proxy / Timeout ADB:** Phải trả về `MANUAL_REVIEW`, cấm gọi `set_follow_failed()`.
  2. **Reload UI lag / Identity chưa xác thực:** Trả về `MANUAL_REVIEW`, không phán nhả bừa bãi.
  3. **Tài khoản đang trong Cooldown:** `cooldown_until_at` còn hiệu lực bắt buộc no-op ở cấp byte, cấm gọi trùng làm dồn toa streak lên 5-6.
  4. **Target ngoài farm (Priority Targets):** Search không ra nick chỉ ghi nhận `skipped`, không bao giờ được coi là lỗi nhả follow.

## 2. Xử Lý Máy Chạm Trần Phiên (Ceiling Drop)
- Khi máy đã follow thành công $\ge 1$ lượt (`used > 0`) rồi bị nhả ở lượt cuối:
  - **Streak:** Giữ nguyên streak hiện tại, không tăng (`streak = max(1, curr_streak)`).
  - **Cooldown:** Chỉ nghỉ 1 ngày xả cache (`cooldown_until_local = today_end_local + 1d`), cấm đày 3 - 15 ngày.
  - **Báo cáo Watchdog:** Bắt buộc ghi nhận máy vào cả `fl_success` (để tính số máy thành công) và `fl_released` (kèm chú thích số lượt đã follow, ví dụ `M59: 3 lượt`). Mẫu số tổng máy = `len(set(fl_success) | set(fl_released))`.

## 3. Bẫy Hiển Thị "Tù Treo" Trên Dashboard & Reconcile O(1)
- **Bản chất lỗi:** File state JSON lưu tĩnh trên đĩa (`follow_state_*.json`). Khi hết hạn cooldown (`now_utc >= cooldown_until_at`), cờ `follow_failed = True` vẫn còn trong file nếu chưa có cron quét tới.
- **Xử lý Dashboard (`follow_health_helper.py`):** Kiểm tra `cooldown_until_at < now` để giải phóng trạng thái về `Hồi phục 1` ngay lập tức, không được chỉ nhìn mỗi cờ `is_failed`.
- **Lệnh giải phóng tự động farm:** Chạy `python D:/Taadaa/tools/reconcile_expired_cooldowns.py` quét 450 file state để hạ cờ `follow_failed = False` cho toàn bộ nick đã mãn hạn.
