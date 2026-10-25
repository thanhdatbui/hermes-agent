# Kiến Trúc Dynamic Shift-Pool 4 Ngày & Đồng Bộ Phiên Nuôi Acc (S2 bám S1)

## 1. Thiết Kế Shift-Pool Dynamic Tuần Tự Theo Độ Khỏe & Đi Đủ 8 Nick (Anti-Starvation)
Hệ thống quản lý tới tầng tài khoản (Account-Level Telemetry), xóa bỏ hoàn toàn việc gán cứng D0/D1/D2/D3 toàn farm cùng chạy 1 row:
- `_ANCHOR_ORDINAL = date(2026, 10, 11).toordinal()`
- `cycle_day = (today.toordinal() - _ANCHOR_ORDINAL) % 4` (0 -> 3)
- `cycle_idx = (today.toordinal() - _ANCHOR_ORDINAL) // 4`

### Phân Bổ Ca Nuôi & Ranh Giới Pool:
- **Ca 1 (Sáng: 06:00 & 08:00):** Pool `{1, 2, 7}`
- **Ca 2 (Trưa: 12:00 & 14:00):** Pool `{3, 4, 8}`
- **Ca 3 (Tối: 18:00 & 20:00):** Pool `{5, 6}`. Riêng Ngày 3 (D2) hoặc ngày dưỡng sinh (D3) bốc thêm **Row Động** theo phễu Đề xuất $\to$ Nhả $\to$ Yếu.

### Quy Luật Bốc Tuần Tự Đi Đủ 8 Nick (Không Bỏ Đói):
- **Phễu Sức Khỏe 6 Tầng (`_follow_rank`):**
  1. 🟢 **Rank 1 - Khỏe (`healthy`):** `graduated=True` hoặc `healthy`.
  2. 🥈 **Rank 2 - Đề xuất (`boosted`):** `is_account_boosted(machine, row) == True`.
  3. 🥉 **Rank 3 - Hồi phục 2 (`probation_tier2`):** `probation_clean_days >= 1`.
  4. 🎖️ **Rank 4 - Hồi phục 1 (`probation_tier1`):** `probation_clean_days == 0` và `fail_streak > 0`.
  5. ⚠️ **Rank 5 - Nhả (`cooldown`):** Dính phạt nhả follow (`is_in_cooldown=True` hoặc `cooldown_until_date`).
  6. 🌱 **Rank 6 - Mặc định / Yếu:** Nick mới hoặc video count thấp nhất.
- **Nguyên lý xoay vòng:**
  * Máy lọc các nick trong Pool chưa chạy trong chu kỳ (`candidates = [r for r in pool if r not in used]`).
  * Sắp xếp theo thứ hạng sức khỏe: `min(candidates, key=lambda r: _follow_rank(machine, r, today))`.
  * Nick đã chạy hôm trước sẽ được lưu vào `used` $\implies$ Ngày tiếp theo máy bốc nick có thứ hạng kế tiếp.
  * Khi tất cả nick trong pool của ca đó đều đã chạy (`not candidates`) $\implies$ Tự động reset `used` của ca đó để bắt đầu vòng tuần tự mới.
  * **Bảo đảm 100%:** Luân phiên đi đủ cả 8 nick trên từng máy, không bao giờ có nick nào bị bỏ đói!

### Hai Tầng Cooldown Tách Biệt Độc Lập:
1. **Tầng Farm (48h Cooldown Lượt Nuôi):**
   * Sau khi một nick chạy xong, máy nghỉ tự nhiên ~48h để chạy các nick còn lại trong pool trước khi quay vòng lại.
2. **Tầng Account (Follow Cooldown Theo Streak Riêng):**
   * Quyền nuôi (Feed + Video) và Quyền Follow là 2 quyền độc lập.
   * Nick bị phạt nhả follow BẮT BUỘC tuân thủ streak riêng của nick đó (Streak 1: 1 ngày, Streak 2-3: 3 ngày...).
   * Khi dính phạt: Hệ thống tự động tắt cờ follow (`rest_day_no_follow: true`), chỉ cho lướt feed xả phạt và up video giữ kênh.

---

## 2. Cơ Chế 3 Phễu Dưỡng Sinh (`resolve_dynamic_account_for_machine`)
Khi rơi vào ca/ngày dưỡng sinh, `resolve_shift_pool_account` raise `ValueError`, tầng `feed_session_workbook.py` tự động kích hoạt 3 lớp phễu chọn nick per-machine:
1. **Lớp 1 (Ưu tiên 1 - Cắn đề xuất):** `is_account_boosted(machine, row, user)` (Follower tăng $\ge 20$, Tim $\ge 50$ trong 7 ngày qua). Giữ nhịp đăng video để ăn view.
2. **Lớp 2 (Ưu tiên 2 - Đi tù / Gỡ hạn chế):** `_is_account_follow_cooldown(machine, row)` (Nick dính nhả follow cần lướt feed xả cooldown).
3. **Lớp 3 (Ưu tiên 3 - Nick non / ít video nhất):** Sắp xếp theo `video_count` tăng dần để kéo nick yếu lên.

---

## 3. Bất Biến "Phiên 2 Bám Phiên 1" (S2 bám S1 100%)
- **Mục tiêu:** Phiên 2 (08h, 14h, 20h - có upload hook) bắt buộc chạy đúng tài khoản đã được nuôi ở Phiên 1 (06h, 12h, 18h) cùng ca trong ngày.
- **Lưu vết:** `record_shift_session_account(machine, row, ca, today_date)` ghi nhận vào `today_shift_sessions[ca][machine] = row`.
- **Đồng bộ Dưỡng Sinh:** Khi Phiên 1 rơi vào nhánh 3 phễu, `feed_session_workbook.py` BẮT BUỘC gọi `record_shift_session_account` ngay khi chọn được nick. Phiên 2 chỉ đọc lại vết này mà không tính lại phễu, chống việc cooldown thay đổi giữa 2 phiên làm lệch nick.
- **Thứ tự kiểm tra Fallback (Crucial Pitfall):** Trong `resolve_shift_pool_account`, điều kiện fallback `cycle_day == 3 or (cycle_day == 2 and ca == 3)` PHẢI ĐẶT TRƯỚC `if machine_key in today_sessions` ở Session 1. Nếu đặt sau, Session 1 của ngày dưỡng sinh có nguy cơ đọc trúng bản ghi cũ từ pool thay vì kích hoạt 3 phễu.
- **Tách bạch Session 2 vs Fallback:**
  * Session 2 LUÔN LUÔN đọc từ `today_sessions[ca_key][machine_key]`. Nếu tìm thấy: log `[SHIFT_POOL_SELECT] ... source=session1_sync` và return ngay. Nếu thiếu: log `[SHIFT_POOL_SYNC_ERROR]` và raise `ValueError`.
  * Khối Fallback chỉ áp dụng cho Session 1: khi thỏa mãn điều kiện fallback, log `[SHIFT_POOL_FALLBACK_TRIGGER]` và raise `ValueError` để chuyển sang 3 phễu.
- **Hệ Thống Structured Telemetry Logging:**
  * `[SHIFT_POOL_SELECT]` kèm các nguồn: `source=session1_sync`, `source=today_cache`, `source=pool_rotation`.
  * `[SHIFT_POOL_FALLBACK_TRIGGER]`: Ghi nhận máy, ca, ngày chu kỳ khi kích hoạt 3 phễu.
  * `[SHIFT_POOL_EXHAUSTED]`: Cảnh báo khi hết nick khả dụng trong pool.
  * `[DYNAMIC_SESSION_SYNC]` & `[DYNAMIC_SESSION_SYNC_ERR]`: Ghi nhận đồng bộ phiên dưỡng sinh trong `feed_session_workbook.py`.
  * Thu hẹp ngoại lệ: Chỉ bắt `(ValueError, KeyError)` khi gọi `resolve_shift_pool_account` thay vì bắt broad `Exception`.
  * Kiểm thử bắt log: Dùng fixture `caplog` với `caplog.at_level(logging.INFO)` để assert bắt đúng chuỗi telemetry trong unit test.

---

## 4. Chuỗi Nối Dây (End-to-End Wiring) & Các Cạm Bẫy Lập Trình (Pitfalls)
1. **Bug `int(args.account_row_index or 1)`:**
   - Trong Python, khi truyền cờ `--account-row-index 0` để chạy dynamic, biểu thức `0 or 1` đánh giá ra `1` $\implies$ luôn bị ép thành Row 1.
   - Sửa chuẩn: `int(args.account_row_index) if args.account_row_index is not None else 1`.
2. **Forward tham số ShiftCa:**
   - `run_tiktok.py`: thêm cờ `--shift-ca {1, 2, 3}` và gán `config["_shift_ca"]`.
   - `run-feed-session.ps1`: thêm `[ValidateRange(1, 3)][int]$ShiftCa` và forward `--shift-ca $ShiftCa`.
3. **Cron Runner (`tiktok_runner.py`):**
   - Tự động map khung giờ: 6/8h $\to$ Ca 1; 12/14h $\to$ Ca 2; 18/20h $\to$ Ca 3.
   - Kích hoạt dynamic: truyền `-Row 0` và `-ShiftCa <ca>`.
   - Hàm `_get_machines_for_row(0)`: Khi `row == 0`, lọc toàn bộ máy có ít nhất 1 slot hợp lệ trong workbook. Tránh tính `slot_idx = row - 1 = -1` (vướng slot 8).
4. **Validation Bounds:**
   - `record_shift_session_account` kiểm tra chặt `1 <= row <= 8` và `ca in (1, 2, 3)`.
   - `_load_state` bọc `try-catch` kiểm tra chuỗi rỗng để chống crash `JSONDecodeError` khi state file bị 0 bytes.
5. **Cạm Bẫy Deploy Drift Giữa Dev Repo (`tiktok-luot nuoi acc`) và Cron Runtime (`Hermes/deploy`):**
   - **Hiện tượng:** Code dynamic `Row 0` đã commit trong `tiktok-luot nuoi acc`, nhưng hôm sau cron vẫn chạy nhặt fixed row cũ (Row 2, 4, 6...).
   - **Nguyên nhân:** Hermes cronjob (`phase9-runner-tiktok-feed`, `tiktok-feed-session-watchdog`) thực thi scripts từ `%LOCALAPPDATA%\hermes\scripts\`, vốn được đồng bộ định kỳ bởi `cron_sync_watchdog.py` từ repo `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`.
   - **Quy trình Deploy bắt buộc sau khi sửa `scripts/hermes_cron/`:**
     1. Đồng bộ file sang deploy repo:
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/tiktok_runner.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py"`
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/tiktok_picker.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_picker.py"`
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" "D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py"`
        `cp "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py"`
     2. Commit thay đổi vào cả 2 repo (`tiktok-luot nuoi acc` và `Hermes`).
     3. Kích hoạt đồng bộ runtime ngay lập tức:
        `python "D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py" --force`
     4. Chạy kiểm chứng dry-run/simulation `_determine_row()` và `_get_machines_for_row(0)` để đảm bảo `effective_feed_row == 0` được kích hoạt.
6. **Cạm bẫy `run-feed-session.ps1` cấm kết hợp `-LocalRun` với `-Machines`:**
   - Khi `tiktok_runner.py` gọi pre-session device gate để lọc `healthy_machines`, nó truyền cả `-LocalRun` và `-Machines`.
   - Nếu `run-feed-session.ps1` giữ guard cũ `if ($LocalRun -and $Machines) { throw ... }`, toàn bộ phiên spawn từ runner sẽ văng lỗi.
   - Sửa chuẩn: Cho phép `-LocalRun` kết hợp `-Machines`, lọc mảng máy tìm thấy từ workbook row theo tập `[int]$m` được truyền vào.
7. **Cạm bẫy Line Budget Gate của `feed_session_watchdog.py` (`<= 1450` dòng):**
   - Bộ test kiến trúc `tests/test_watchdog_architecture_gate.py::test_feed_session_watchdog_line_budget` kiểm soát chặt chẽ độ dài `feed_session_watchdog.py <= 1450` dòng.
   - Khi chèn thêm logic/hook (ví dụ `incident_emitter`), BẮT BUỘC phải nén gọn các cấu trúc tĩnh (như list-dict `CLUSTERS` trên 1 dòng) hoặc loại bỏ dòng trống dư thừa để không vi phạm kiến trúc gate.
8. **Kiến Trúc Two-Phase Commit & Auto-Retry Giao Tin Telegram (`feed_session_watchdog.py`):**
   - **Vấn đề:** Hermes scheduler chạy `no_agent: True` không có hàng đợi retry khi gặp lỗi mạng tạm thời (`httpx.ProxyError: Host unreachable`). Nếu script watchdog commit state trước khi Hermes gửi tin thành công, báo cáo phiên nuôi sẽ biến mất vĩnh viễn (do các tick sau script im lặng).
   - **Giải pháp Two-Phase Commit:**
     * *Pha 1 (Pending Claim):* Khi có report mới, lưu vào `pending_delivery: {"session_key": ..., "message": ...}`, chưa commit vào `reported_sessions`, rồi in stdout.
     * *Pha 2 (Hermes Telemetry Verification):* Ở tick kế tiếp, đọc `jobs.json` của Hermes (`_get_hermes_delivery_error(mode)`). Nếu có `last_delivery_error`, tự động re-emit `pending["message"]` để Hermes retry ngay. Chỉ khi `last_delivery_error is None`, mới chuyển `session_key` vào `reported_sessions` và dọn `pending_delivery`.
