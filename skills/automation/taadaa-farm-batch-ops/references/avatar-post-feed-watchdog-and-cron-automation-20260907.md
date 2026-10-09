# Watchdog Tự Động Kích Hoạt Upload Avatar Sau Ca 3 Nuôi Feed (2026-09-07)

## 1. Bối cảnh & Yêu cầu vận hành
Khi người dùng yêu cầu: *"Có cách nào đặt watcher chạy upload avatar cho all row cuối của ngày 1 lần k. Tức row 5 và 6 sau khi phiên nuôi cron chạy xong thì sẽ chạy luôn batch up avatar, mỗi row nick 1 lần thôi"*.
- **Cấm chạy đè (Feed Idle Gate):** Không thể kích hoạt batch upload avatar trong khi Phiên 3 Ca 3 nuôi feed đang chạy vì gây xung đột giao diện TikTok, mất focus và tranh chấp device lock.
- **Giới hạn khung giờ (Window Guard):** Batch up avatar phải chạy gọn trong khoảng từ sau Phiên 3 (22:30 - 00:45) và kết thúc trước 01:00 để không tranh chấp với chuỗi Reg ban đêm (`night-chain-reg-pipeline`).
- **Idempotency tuyệt đối ("Mỗi row nick 1 lần duy nhất"):** Nick/máy nào đã up avatar thành công cho row đó thì vĩnh viễn không bao giờ up lại.

---

## 2. Kiến trúc & Vị trí Module
- **Script Canonical In-Repo:** `D:\Taadaa\Tiktok-video\scripts\avatar_post_feed_watchdog.py`
- **Unit Test Suite:** `D:\Taadaa\Tiktok-video\tests\test_avatar_post_feed_watchdog.py` (10/10 tests passed)
- **Hermes Cron Wrapper:** `C:\Users\Kibe\AppData\Local\hermes\scripts\avatar_post_feed_watchdog_wrapper.py`
- **Hermes Cron Job:** `avatar-post-feed-watchdog` (Lịch: `*/10 22,23,0 * * *`, `no_agent: true`, deliver: `origin`)
- **Idempotency Ledger:** `D:\Taadaa\runtime\kibe\cron-state\avatar_upload_history.json`

---

## 3. Các bước kiểm tra & Cơ chế thực thi (Pre-flight Ladder)
1. **Phân định Row tự động theo Logical Day:**
   - Nếu giờ hiện tại `< 02:00`: thuộc logical day của ngày hôm trước (`now - 1 ngày`).
   - Ngày Lẻ -> Chọn **Row 5** (`Tik5.xlsx`).
   - Ngày Chẵn -> Chọn **Row 6** (`Tik6.xlsx`).
   - Hỗ trợ cờ `--row 5` hoặc `--row 6` để ép chạy row cụ thể khi cần.
2. **Khung giờ & Idle Gate:**
   - Khung giờ hợp lệ: `22:30` đến `00:45`. Nếu ngoài khung giờ -> in `[SKIP]` và thoát êm dịu (exit 0).
   - Kiểm tra tiến trình nuôi feed qua `psutil.process_iter(['name', 'cmdline'])` quét các signature:
     `multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`, `hermes_cron_runner.py`, `run_tiktok.py`.
     Nếu phát hiện runner đang bận -> in `[SKIP]` và thoát êm dịu để chờ tick kế tiếp.
   - Hỗ trợ cờ `--force` để bypass khung giờ và feed runner check khi test hoặc chạy bù thủ công.
3. **Lọc Idempotency ("Mỗi row nick 1 lần"):**
   - Đọc danh sách máy từ workbook `D:\OneDrive\TaadaaData\kibe\Tik{row}.xlsx`.
   - Đối soát với ledger `avatar_upload_history.json` theo key `"{machine}_{row}"`.
   - Loại bỏ toàn bộ các máy đã có `"status": "success"`.
   - Nếu danh sách máy cần up rỗng (`len(pending) == 0`) -> in `[DONE]` và thoát 0.
4. **Sinh Assignment Manifest & Dispatch Launcher:**
   - Ghi file manifest ra `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-row{row}.json` (schema v1, owner `hermes-kibe-avatar`).
   - Kích hoạt launcher:
     ```powershell
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
       -Tik <row> `
       -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-row<row>.json" `
       -WorkerId "hermes-kibe-avatar" `
       -ForceAvatarMachineList "<comma_separated_machines>" `
       -MaxParallel 40 `
       -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
     ```
   - Thiết lập biến môi trường `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45`.
5. **Cập nhật Ledger State & Báo cáo:**
   - Quét thư mục batch run mới nhất trong `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik{row}_*`.
   - Đọc `summary.csv`, lọc các máy có `ExitCode == 0` và `Verified == True` để ghi nhận `status: "success"` vào `avatar_upload_history.json` (ghi atomic qua file tạm `.tmp`).
   - In tóm tắt báo cáo chuẩn: Tổng máy, Thành công, Thất bại.

---

## 4. Lệnh chạy tay & Kiểm tra nhanh (Canary / Dry-run)
- **Kiểm tra Dry-run (không đụng chạm máy thật):**
  ```bash
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" "D:/Taadaa/Tiktok-video/scripts/avatar_post_feed_watchdog.py" --dry-run --force
  ```
- **Chạy bù ép buộc cho một Row cụ thể:**
  ```bash
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" "D:/Taadaa/Tiktok-video/scripts/avatar_post_feed_watchdog.py" --row 5 --force
  ```
