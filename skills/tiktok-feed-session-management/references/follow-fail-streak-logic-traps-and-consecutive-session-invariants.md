# Follow Fail Streak Logic Traps & Consecutive Session Invariants

## Bối cảnh sự cố
Khi đối soát "Sổ Bệnh Án" Follow Dashboard trên farm TikTok:
- Nick `@lu.huyn926` (Máy 31 Row 1) vừa mới bị nhả 1 ca gần nhất (`10-31: 0 lượt`), trước đó ca `10-27` đã follow thành công `+9 lượt` nhưng hệ thống lại xếp vào `Streak lỗi: 2`.
- Nick `@tolmavhj12k` (Máy 8 Row 1) bị nhả liên miên qua 6 ca liên tiếp từ `10-05` đến `11-01` (`10-05`, `10-15`, `10-23`, `10-25`, `10-27`, `11-01`) nhưng hệ thống lại chỉ ghi nhận lẹt đẹt `Streak lỗi: 2`.

---

## 2 Cạm bẫy Logic Cốt Lõi trong `follow_state.py`

### 1. Bẫy Tích lũy Streak Mù (Blind Streak Accumulation across Successes)
- **Cơ chế lỗi:**
  Trong hàm `set_follow_failed()` của `follow_state.py`:
  ```python
  diff_days = (today_dt - last_dt).days
  if 1 <= diff_days <= max_diff_days:
      streak = min(10, curr_streak + 1)
  else:
      streak = 1
  ```
- **Hệ quả:** Logic tính streak chỉ dựa trên khoảng cách số ngày (`diff_days <= max_diff_days`) so với `last_failed_date` trước đó mà **hoàn toàn bỏ qua việc giữa 2 mốc thời gian đó nick đã có ca chạy follow thành công (follows > 0)**.
- **Biểu hiện:** Ca `10-27` đã follow được +9 lượt (chứng minh nick hoàn toàn bình thường). Đến ca `10-31` bị nhả, vì `diff_days = 4 <= 7`, hệ thống mù quáng lấy `curr_streak (1) + 1 = 2`, phạt oan nick vừa mới nhả lần đầu sau khi đã chạy tốt.
- **Invariant khắc phục:** BẮT BUỘC kiểm tra lịch sử follow: Nếu giữa `last_failed_date` và `today` tồn tại bất kỳ lượt follow thành công nào (`any(ts > last_failed_at)`), streak BẮT BUỘC phải reset về `streak = 1`.

---

### 2. Bẫy Đứt Gãy Streak do Cửa Sổ Ngày Tuyệt Đối (Grace Window Reset Trap)
- **Cơ chế lỗi:**
  Hệ thống gán cứng cửa sổ ân hạn theo số ngày dương lịch (`max_diff_days = 7` cho streak 1, `9` cho streak 2...). Nếu `diff_days > max_diff_days`, streak tự động reset về `1`.
- **Hệ quả:** Trên Phone Farm, các máy/nick thường chạy xoay tua (alternate-day/shift-pool), nghỉ lễ, bảo trì thiết bị hoặc nằm trong danh sách dưỡng. Khi khoảng cách giữa 2 ca chạy thực tế vượt quá 7 ngày (như từ `10-05` đến `10-15` là 10 ngày), dù ca trước đó bị 0 lượt và ca này tiếp tục 0 lượt, hệ thống vẫn coi là "quá hạn" và reset `streak` về 1, sau đó ca tiếp theo mới lên 2.
- **Biểu hiện:** Một nick bị TikTok bóp reach / nhả dai dẳng suốt cả tháng với chuỗi 6 ca gãy liên tiếp không có lượt follow nào thành công vẫn chỉ hiển thị `Streak 2`, khiến watchdog và hệ thống không nhận diện được nick bị "Persistent Jail" (Streak >= 4) để đưa vào diện cách ly 15 ngày.
- **Invariant khắc phục:** Phải tính streak theo **số ca chạy thực tế liên tiếp bị gãy (consecutive failed sessions without successful follow)** thay vì khoảng cách ngày dương lịch tuyệt đối. Cửa sổ thời gian chỉ nên dùng để xóa án tích khi nick đã có thời gian nghỉ dưỡng sạch sẽ (Clean probation / graduated) mà không bị gãy tiếp.
