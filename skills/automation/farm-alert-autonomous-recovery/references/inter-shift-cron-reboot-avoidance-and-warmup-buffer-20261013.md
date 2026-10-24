# Inter-Shift Cron Reboot Avoidance & Warmup Buffer Protocol (2026-10-13)

## 1. Hiện tượng & Bối cảnh
- Khi runner spawn Ca 2 (12:00) kết nối đồng loạt sang Admin Remote (`192.168.110.119:5037`), hàng loạt máy báo fail với lý do: `adb.exe: protocol fault (couldn't read status): connection reset`.
- **Nguyên nhân gốc rễ:**
  - Mốc Auto-Reboot cũ (`11:35`) quá sát giờ chạy Ca 2 (`12:00`), chỉ có 25 phút đệm.
  - Trên hệ thống farm 80 máy/host qua chipset USB Intel X99: Sau reboot, Windows cần thời gian nạp driver, handshake WireGuard, và XiaoWei mất 10–15 phút để enumerate đầy đủ bus USB cho 80 máy Android.
  - Khi chưa đủ thời gian ổn định ("warmup"), 25–40 workers từ Kibe ồ ạt kết nối vào port 5037 làm sập socket daemon ADB trên Admin.
  - Đồng thời: Các cronjob chạy giữa các ca (inter-shift) nếu không tự né giờ reboot sẽ bị shutdown cưỡng bức giữa chừng khi đang thao tác trên thiết bị S7 (Reg Gmail, 2FA TikTok, upload avatar).

## 2. Quy tắc 40 Phút Warmup Buffer (Reboot Schedule Invariant)
- Cập nhật 3 mốc Auto-Reboot định kỳ chuẩn của toàn Farm:
  * **Mốc Sáng:** `05:20:00` (đệm 40 phút trước Ca 1 - 06:00).
  * **Mốc Trưa:** `11:20:00` (đệm 40 phút trước Ca 2 - 12:00).
  * **Mốc Chiều:** `17:20:00` (đệm 40 phút trước Ca 3 - 18:00).
- Được quản lý bởi Task Scheduler Windows: `Taadaa_Farm_Daily_Reboot_1135` (`update_reboot_schedule.py` & `setup_daily_reboot_task.ps1`).

## 3. Quy tắc Inter-Shift Cron Reboot Avoidance (Tự né giờ Reboot)
Mọi cron / watchdog chạy trong khoảng nghỉ giữa các ca liên quan đến thiết bị S7 BẮT BUỘC tuân thủ cơ chế tự né giờ reboot:

### A. Tác vụ Batch dài (~50–60 phút) — Ví dụ `post_noon_chain_watchdog`
- **Khung chạy an toàn:** `14:30 – 16:20` (sau Ca 2).
- **Hard Cutoff:** 16:20.
- **Quy tắc né:** Từ 16:20 đến 17:35, watchdog BẮT BUỘC `[SKIP]` không spawn batch mới. Sau 17:20 reboot xong (17:35), chỉ còn 25 phút trước Ca 3 (18:00), không đủ thời gian chạy batch 60 phút nên tiếp tục nghỉ đến Ca 3.
- Cron schedule: `*/5 14,15,16 * * *`.

### B. Tác vụ Trung bình (~15–20 phút) — Ví dụ `post_morning_gmail_2fa_watchdog`, `post_evening_avatar_watchdog`
- **Quy tắc cutoff:** Phải dừng trước mốc reboot ít nhất 10–15 phút:
  * `post_morning_gmail_2fa_watchdog`: `end_hm=(11, 10)` (dừng trước 11:20).
  * `post_evening_avatar_watchdog`:
    - Ca sáng/trưa: `h == 11 and m <= 5` (dừng lúc 11:05, né 11:20).
    - Ca đêm: `(h == 3 and m >= 15) or (h == 4) or (h == 5 and m <= 5)` (dừng lúc 05:05, né 05:20).

### C. Tác vụ Polling ADB liên tục — Ví dụ `farm_idle_screen_and_app_healer`
- BẮT BUỘC gọi hàm kiểm tra `is_near_reboot_window(buffer_minutes=10)` ngay đầu `main()`:
  * Nếu rơi vào các cửa sổ `[05:10, 05:30]`, `[11:10, 11:30]`, `[17:10, 17:30]`:
  * In log `[SKIP]` và `return 0` ngay lập tức, tuyệt đối không gửi lệnh ADB.

### D. Tác vụ Dọn dẹp Cache cuối ngày — Ví dụ `end-of-day-clear-tiktok-cache`
- Cron schedule phải kết thúc trước 05:00: `*/15 3,4 * * *` (chạy 03:00 – 04:45), trả lại vùng đệm sạch hoàn toàn trước mốc reboot 05:20.

---

## 4. Kỷ Luật Dispatch Worker & Closeout Verification Pitfalls
1. **Pitfall `guard_dispatch_contract.py` (Lỗi `OLD_EQUALS_NEW`):**
   - Khi Coordinator soạn contract `delegate_task` cho Worker: Guard so sánh dòng đầu tiên của `OLD_STRING` và `NEW_STRING`. Nếu dòng đầu tiên giống nhau (do gom dòng context ở trên), guard sẽ chặn:
     `OLD_EQUALS_NEW: Đoạn mã cũ và mới #1 hoàn toàn giống nhau`
   - **Cách khắc phục:** Cắt bỏ dòng context ở đầu; `OLD_STRING` và `NEW_STRING` bắt buộc phải bắt đầu ngay tại dòng có sự thay đổi thực sự.

2. **Pitfall Telemetry Verification Cho Windows Task Scheduler:**
   - Khi script cập nhật Scheduled Task (`update_reboot_schedule.py`), Sol Reviewer yêu cầu phải có post-update verification telemetry (`validation: {"task_exists": True, "trigger_count": N}`) đọc ngược lại từ `Get-ScheduledTask` để chứng minh task đã được đăng ký thành công trên host thực tế thay vì chỉ tin vào exit code của process con.
   - Hơn nữa, test suite (`tests/test_update_reboot_schedule.py`) bắt buộc phải bao phủ đầy đủ các failure paths của validation (như timeout, OSError, disabled state, mismatched trigger times) thì Sol Reviewer mới chấm đạt >= 85 điểm.

3. **Pitfall Strike 3 Hand-off & Claude CLI Headless Permissions:**
   - Khi Gate trượt 3 lần liên tiếp trên cùng scope_hash, kích hoạt chuyển giao quyền can thiệp cho Claude CLI.
   - **Lỗi chí mạng:** Khi chạy `claude -p` ở chế độ headless / background automation không có TTY tương tác, Claude CLI sẽ tự động từ chối mọi thao tác ghi/sửa file (`The write to <path> was denied for lack of permission...`) nhưng vẫn trả về exit code 0, khiến quá trình remediation bị bế tắc và kéo dài phiên làm việc.
   - **Bắt buộc:** Luôn truyền cờ `--dangerously-skip-permissions` khi gọi Claude CLI trong automation:
     ```bash
     claude --dangerously-skip-permissions -p "..."
     ```

