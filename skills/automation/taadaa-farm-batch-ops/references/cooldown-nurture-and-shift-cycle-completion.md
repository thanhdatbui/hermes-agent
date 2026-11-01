# Quy Chuẩn Nuôi Nick Cooldown Dưỡng Sinh & Hoàn Tất Chu Kỳ Xoay Tua

## 1. Nguyên Tắc Cốt Lõi Về Nick Cooldown (Bị Nhả / Đi Tù)
- **Nick bị Cooldown (Follow Drop / Phạt Streak) VẪN ĐƯỢC NUÔI BÌNH THƯỜNG**:
  - Không có chuyện "loại bỏ nick dính cooldown ra khỏi lịch nuôi".
  - Nuôi lướt feed, xem video, thả tim tự nhiên là bước dưỡng sinh bắt buộc để làm ấm session và giải án phạt.
- **Chỉ ngắt thao tác Follow ở bước cuối**:
  - Hook follow (`_run_follow_hook`) ở cuối phiên nuôi tự động kiểm tra trạng thái (`_is_account_follow_cooldown`).
  - Nếu nick đang trong thời gian phạt `follow_failed` hoặc chưa qua `cooldown_until_date` $\to$ bỏ qua follow (`skipped: follow-released-daily-cooldown`), tuyệt đối không follow mù.

---

## 2. Bẫy Kẹt Vòng Lặp Không Xoay Tua Chu Kỳ (Deadlock Trap)
- **Nguyên nhân**:
  - Script điều phối ca (`multi_machine_feed_session.py`) trước đây chỉ gọi `mark_shift_account_cycle_completed` khi phiên follow trả về `status == "OK"`.
  - Các nick bị skip follow do Cooldown bị trả về `status == "skipped"` $\to$ không được ghi nhận hoàn thành chu kỳ.
  - Sang hôm sau, máy thấy nick này "hôm qua chưa hoàn thành chu kỳ" $\to$ lại tiếp tục bốc đúng nick đó ra chạy lại, khiến máy ngày nào cũng lôi đúng 1 nick ra cày mà không chịu xoay sang các Row khác trong Pool.
- **Khắc phục chuẩn hóa**:
  ```python
  is_success_run = proc.returncode == 0 and result.get("status") == "OK" and not bool(result.get("failed"))
  is_cooldown_skip = result.get("status") == "skipped" and any(k in str(result.get("reason", "")).lower() for k in ("cooldown", "follow-released"))
  if shift_ca and (is_success_run or is_cooldown_skip):
      mark_shift_account_cycle_completed(account.machine, account.account_row_index, shift_ca)
  ```
  - Khi một nick được nuôi xong và bỏ qua follow hợp lệ do cooldown $\to$ vẫn tính là hoàn thành lượt nuôi của ngày để máy nhường lượt xoay tua sang Row kế tiếp trong Pool ngày mai.

---

## 3. Thứ Hạng Phễu Pick Nick Trong Shift Pool
- Không được tự ý bịa đặt khái niệm "pool nick sạch" hay đảo lộn bảng thứ hạng.
- Thứ tự pick nick chuẩn trong từng Ca (`_follow_rank`):
  1. `Rank 1`: Nick tốt nghiệp / khỏe mạnh (`graduated` / `healthy`).
  2. `Rank 2`: Nick cắn đề xuất (`is_account_boosted`) $\to$ ưu tiên đăng video giữ đà.
  3. `Rank 3`: Nick thử thách sạch án (`probation_clean_days >= 1`).
  4. `Rank 4`: Nick đang dưỡng sinh / dính fail streak (`fail_streak > 0`) $\to$ vẫn nuôi dưỡng sinh.
  5. `Rank 5`: Nick đang chờ mốc cooldown.
  6. `Rank 6`: Nick thường chưa phân hạng.
