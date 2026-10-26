# Dynamic Pool Row 0 vs Cron Runner Rest-Day Flag Parity

## 1. Bản Chất Vấn Đề (The Dual-Level Rest Day Conflict)
Khi chuyển đổi hệ thống Farm từ Fixed Row sang **Dynamic Shift Pool (Row 0)**:
- Ở tầng logic bên trong (`shift_pool_selector.py` & `feed_session_workbook.py`): Hệ thống đã bỏ hoàn toàn lịch cố định theo ngày (`cycle_day == 3`), chuyển sang cơ chế bốc xoay tua theo độ khỏe (Rank 1-6) và state-driven 100%. Khi nick đủ điều kiện, runner cho phép lướt feed + đi follow bình thường.
- Ở tầng wrapper bên ngoài (`tiktok_runner.py`): Vẫn còn bảng lịch cứng `_SCHEDULE` theo ngày dương lịch `(now.date().toordinal() - BASE_ORDINAL) % 4`. Khi rơi vào ngày 4 (`cycle_day == 3`), slot trả về `None`, wrapper tự động gán `is_rest_day = True`.
- **Hậu quả:** Wrapper inject biến môi trường toàn cục `child_env["TAADAA_REST_DAY_NO_FOLLOW"] = "1"` vào tiến trình con PowerShell. Khi các máy con chạy, `multi_machine_feed_session.py` thấy biến này liền cưỡng chế skip toàn bộ follow hook với reason `"rest-day-follow-disabled-pure-feed"`, khiến Watchdog báo cáo 100% máy bị "Đang dưỡng sinh" dù code bên trong đã bỏ ngày dưỡng sinh.

## 2. Quy Tắc Triệt Tiêu Xung Đột (Invariants)
1. **Dynamic Overrides Static Schedule:** Khi `effective_feed_row == 0` (chế độ Dynamic Pool), cờ `is_rest_day` ở tầng wrapper BẮT BUỘC phải được ép về `False`:
   ```python
   effective_feed_row = 0 if (use_dynamic and shift_ca is not None) else row
   if effective_feed_row == 0:
       is_rest_day = False
   ```
2. **Khóa Biến Môi Trường Toàn Farm:** Hàm spawn session (`_spawn_feed_session`) chỉ được phép bật `TAADAA_REST_DAY_NO_FOLLOW = "1"` khi và chỉ khi đang chạy Fixed Row (`row != 0`):
   ```python
   if is_rest_day and row != 0:
       child_env["TAADAA_REST_DAY_NO_FOLLOW"] = "1"
   else:
       child_env.pop("TAADAA_REST_DAY_NO_FOLLOW", None)
   ```
3. **Quy Trình 3 Bước Đồng Bộ Runtime (Anti-Deploy Drift):**
   Mọi thay đổi trên `scripts/hermes_cron/tiktok_runner.py` hoặc `feed_session_watchdog.py` trong repo `tiktok-luot nuoi acc` BẮT BUỘC phải qua 3 bước:
   - Bước 1: Copy file sang `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`.
   - Bước 2: Chạy `python "D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py" --force` để đẩy vào `%LOCALAPPDATA%\hermes\scripts\` và OneDrive Shared.
   - Bước 3: Kiểm tra pytest regression (`test_shift_pool_selector.py`, `test_tiktok_runner_healing.py`, `test_feed_session_watchdog.py`).

## 3. Bài Học Closeout Gate & Architecture Line Budget
1. **Kiểm Tra Line Budget Trước Khi Thẩm Định:** Khi file monolithic (`feed_session_watchdog.py`) tăng dòng do tính năng mới (ví dụ two-phase delivery, incident emitter), kiểm tra ngay file gate architecture `tests/test_watchdog_architecture_gate.py`. Nếu vượt ngưỡng, phải nâng budget hoặc tách module vào `scripts/watchdog/`.
2. **Reviewer Scorecard 85+ Requirement:** Để Reviewer Closeout Gate chấm $\ge 85$:
   - Không được chỉ sửa code runner mà thiếu unit test cô lập.
   - BẮT BUỘC có unit test mô phỏng trực tiếp hành vi: (a) test `_spawn_feed_session` không gán biến môi trường cấm khi `row == 0`, (b) test `main()` override `is_rest_day = False` khi `effective_feed_row == 0`.
   - Có unit test trực tiếp sẽ nâng điểm từ mức 78 lên 92+ (Verdict: APPROVED).
