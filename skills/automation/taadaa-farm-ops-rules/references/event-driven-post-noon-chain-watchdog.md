# Event-driven Post-Noon Chain Watchdog (Feed Session -> Reg Gmail -> 2FA TikTok)

## Ngữ cảnh & Mục tiêu
Chuỗi tự động hóa sau ca trưa gồm 2 Phase:
1. Phase 1: Reg Gmail (`D:\Taadaa\register gmail\run_all.ps1`).
2. Phase 2: Add 2FA TikTok (`D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner\run_batch_live_2fa.py --live --max-workers 10`).

## Nguyên tắc Điều phối & Preflight
1. **Kiểm tra tiến trình Feed Session (`multi_machine_feed_session` / `run-feed-session.ps1`)**:
   - Khi ca nuôi đang chạy, các thiết bị bị chiếm dụng hoặc lock qua `automation-core/device-locks`.
   - CẤM chạy chen ngang khi ca nuôi chưa hoàn thành hoặc chưa nhả lock thiết bị.
2. **Kiểm tra Device Locks O(1)**:
   - Thư mục lock: `C:\Users\Kibe\AppData\Local\automation-core\device-locks` và `C:\Users\Kibe\.codex\device-locks`.
   - Hàm chuẩn: `has_active_device_locks()` kiểm tra cả file `.json` (trạng thái `active`, `running`, `queued`, `blocked`) và `.lock`.
3. **Mẫu chạy nền Event-driven (Terminal Background Process)**:
   - Khi ca nuôi đang diễn ra, Coordinator KHÔNG block foreground timeout (max 600s).
   - Khởi chạy tiến trình nền qua `terminal(background=true, notify_on_complete=true)` với vòng lặp thăm dò `wmic` + `post_noon_chain_watchdog.py` check.
   - Khi hết ca và nhả lock, tự động kích hoạt `python post_noon_chain_watchdog.py --force`.
4. **Gate 6 Media Evidence**:
   - Khi báo cáo hiện trường, luôn capture screencap canary O(1) qua serial máy (hoặc inspect_machine) và đính kèm `MEDIA:<path_anh>`.
