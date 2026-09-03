# Device Lock Release & Operational Separation

Use this reference when operating, releasing, or diagnosing Android farm device locks.

## Core Directives

1. **Direct Operational Command & Emergency Stop**:
   - Khi user yêu cầu "dừng hết" / "tắt cron":
     1. Pause ngay các cron nuôi feed: `phase9-runner-tiktok-feed`, `phase9-watcher-tiktok-feed`, `tiktok-feed-session-watchdog`.
     2. Kill các tiến trình runner (`run_tiktok.py`, `run-feed-session.ps1`) nếu còn chạy ngầm.
   - Khi user yêu cầu "nhả lock máy X", "mở khóa máy XX" hoặc "unlock all":
     1. Di chuyển các file `machine_<N>.lock.json` và `serial_<serial>.lock.json` sang thư mục quarantine `~/.codex/device-locks-reaped/manual-unlock-<timestamp>` ngay lập tức.
     2. Đảm bảo chạy lại script kiểm tra `watch_device_locks.py` để xác nhận 0 active locks (tránh bot Telegram tiếp tục spam nhóm Report Lock Device).
   - Không được gắn các điều kiện kiểm tra phức tạp của scheduler (như frozen cohort artifact, assignment manifest digest, cron state) vào làm điều kiện tiên quyết để nhả lock.

2. **Lock Release vs Batch Preflight Separation**:
   - **Device Lock**: Là cơ chế bảo vệ trạng thái vật lý của điện thoại tránh bị nhiều tool chiếm dụng cùng lúc.
   - **Cohort / Manifest**: Là kế hoạch điều phối phiên batch feed/nuôi nick theo lịch.
   - Hai cơ chế này hoàn toàn độc lập: nhả lock máy không phụ thuộc vào việc máy đó có nằm trong cohort của ngày hôm đó hay không.

3. **Safe Backup Procedure**:
   - Luôn dùng `shutil.move` chuyển sang backup có timestamp thay vì xóa cứng (`unlink`).
   - Bỏ qua các file cooldown cấu hình (như `reg_daily_cooldowns.json`), chỉ nhả file lock thiết bị.
