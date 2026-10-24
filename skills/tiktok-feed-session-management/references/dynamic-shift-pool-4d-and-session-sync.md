# Kiến Trúc Dynamic Shift-Pool 4 Ngày & Đồng Bộ Phiên Nuôi Acc (S2 bám S1)

## 1. Thiết Kế Shift-Pool Luân Phiên Sinh Học (96h)
Farm vận hành chu kỳ 4 ngày (96h) cố định neo theo ngày tuyệt đối:
- `_ANCHOR_ORDINAL = date(2026, 10, 11).toordinal()`
- `cycle_day = (today.toordinal() - _ANCHOR_ORDINAL) % 4` (0 -> 3)
- `cycle_idx = (today.toordinal() - _ANCHOR_ORDINAL) // 4`

### Phân Bổ Ca Nuôi & Hàng Tài Khoản:
- **Ca 1 (Sáng: 06:00 & 08:00):** Pool `{1, 2, 7}`
- **Ca 2 (Trưa: 12:00 & 14:00):** Pool `{3, 4, 8}`
- **Ca 3 (Tối: 18:00 & 20:00):** Pool `{5, 6}`

### Lịch Trình Chu Kỳ 4 Ngày:
- **Ngày 1 (D0):** Rank 1 khỏe $\to$ Ca 1: Row 1, Ca 2: Row 3, Ca 3: Row 5.
- **Ngày 2 (D1):** Rank 2 $\to$ Ca 1: Row 2, Ca 2: Row 4, Ca 3: Row 6.
- **Ngày 3 (D2):** Rank 3 $\to$ Ca 1: Row 7, Ca 2: Row 8. Riêng **Ca 3 tối hết nick trong pool `{5, 6}` $\to$ Fallback 3 Phễu Dưỡng Sinh**.
- **Ngày 4 (D3):** **Cả 3 Ca đều là Dưỡng Sinh $\to$ Fallback 3 Phễu Dưỡng Sinh**.

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
