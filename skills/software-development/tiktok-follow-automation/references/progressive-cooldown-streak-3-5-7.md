# Progressive Cooldown Streak 3-5-7 Ngày (follow_state.py)

**Áp dụng:** Hệ thống TikTok Follow Runner (`follow_runner.core.follow_state`)  
**Cập nhật:** 2026-10-02 (Quy tắc streak 3-5-7 ngày thay thế cho daily/4d/7d cũ).

---

## 1. Bối cảnh & Mục đích

Khi tài khoản TikTok bị nhả follow (unfollow shadowban hoặc rate-limit bởi TikTok), cần áp dụng Progressive Backoff Cooldown để tài khoản có đủ thời gian hạ nhiệt, tránh việc tiếp tục follow làm nick bị phạt nặng hơn hoặc chuyển thành hard block.

Quy tắc trước đây (Streak 1: trong ngày, Streak 2: 4 ngày, Streak >= 3: 7 ngày) khiến nick bị nhả lần đầu được mở lại quá sớm trong cữ chạy kế tiếp, dẫn đến tỷ lệ tái phạt cao. Quy tắc mới áp dụng chu kỳ cách ly kéo dài hơn: **3 - 5 - 7 ngày**.

---

## 2. Chi tiết Quy tắc Cooldown & Grace Window

### Cooldown Duration (`set_follow_failed`)
- **Streak 1 (Bị nhả lần đầu):** Nghỉ **3 ngày** (Cooldown đến `today_end_local + timedelta(days=3)` lúc 23:59:59 local).
- **Streak 2 (Bị nhả 2 cữ liên tiếp):** Nghỉ **5 ngày** (Cooldown đến `today_end_local + timedelta(days=5)`).
- **Streak >= 3 (Tái phạm nhiều lần):** Nghỉ **7 ngày** (1 tuần, Cooldown đến `today_end_local + timedelta(days=7)`).

### Grace Window (Tính streak liên tiếp giữa các lần fail)
Khi tính toán `diff_days = (today_dt - last_dt).days`:
- **Streak <= 1:** `max_diff_days = 7` (3 ngày cooldown + 4 ngày scheduling grace).
- **Streak == 2:** `max_diff_days = 9` (5 ngày cooldown + 4 ngày scheduling grace).
- **Streak >= 3:** `max_diff_days = 11` (7 ngày cooldown + 4 ngày scheduling grace).

Nếu `1 <= diff_days <= max_diff_days`, streak tăng: `min(10, curr_streak + 1)`.  
Nếu vượt quá `max_diff_days` hoặc lần đầu bị nhả, streak bắt đầu lại từ `1`.

---

## 3. Quy tắc cập nhật Test Suite (`test_follow_state.py`)

Khi thay đổi sang chu kỳ 3-5-7 ngày:
1. `test_follow_failed_progressive_backoff_lifecycle`:
   - Streak 1: fail ngày 27/08 -> `cooldown_until_date` là `2026-08-30` (3 ngày sau). Hết hạn và mở lại vào sáng 31/08.
   - Streak 2: fail ngày 31/08 -> `cooldown_until_date` là `2026-09-05` (5 ngày sau). Hết hạn và mở lại vào sáng 06/09.
   - Streak 3: fail ngày 06/09 -> `cooldown_until_date` là `2026-09-13` (7 ngày sau). Hết hạn và mở lại vào sáng 14/09.
2. Các test boundary, subsecond, naive interop:
   - Các assertion kiểm tra "unblock on next day" cho Streak 1 cần được điều chỉnh sang ngày sau khi hết hạn 3 ngày (thay vì 1 ngày hoặc 48h cũ).
3. Reset streak: Khi follow thành công (`mark(..., "followed")`), streak reset về 0 và xóa toàn bộ cooldown flags.

---

## 4. Telemetry & Audit Logging (`last_cooldown_decision`)

Để phục vụ giám sát và audit đối soát sau phiên, mỗi lần `set_follow_failed()` ra quyết định:
- **Structured Log**:
  `logger.info("[COOLDOWN_BACKOFF] Machine %s (row %s): streak=%d, cooldown_until_date=%s (until %s), grace_window=%dd", self.machine, self.account_row_index, streak, self._data["cooldown_until_date"], self._data["cooldown_until_at"], max_diff_days)`
- **Audit Metadata (`last_cooldown_decision`)**:
  Lưu trực tiếp vào state JSON với schema chuẩn:
  ```python
  self._data["last_cooldown_decision"] = {
      "streak": streak,
      "cooldown_until_date": self._data["cooldown_until_date"],
      "cooldown_until_at": self._data["cooldown_until_at"],
      "grace_window_days": max_diff_days,
      "decided_at": now_iso,
  }
  ```
- **Lưu ý triển khai**: Cần tính `max_diff_days` dựa theo `curr_streak` ngay đầu hàm `set_follow_failed()` để đảm bảo telemetry luôn có đầy đủ biến kể cả khi lần đầu bị nhả (`last_failed_date` trống).
