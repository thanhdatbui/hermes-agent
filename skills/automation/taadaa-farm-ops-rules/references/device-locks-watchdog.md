# Device Locks Watchdog & Dead-Owner Reaping Operations

Use this reference when operating, inspecting, or debugging the device locks watchdog, reaper, and reporting mechanism.

## Core Properties
- **Watchdog Script**: `C:\Users\Kibe\AppData\Local\hermes\scripts\watch_device_locks.py`
- **Watchdog Cron ID**: `71c2a1b6268c` (`device-locks-watchdog`, schedule `every 15m`)
- **Reaper Cron ID**: `b63730cc5c85` (`reap-dead-owner-locks`, schedule `*/15 * * * *`)
- **Lock Storage**: `~/.codex/device-locks/machine_<N>.lock.json` và `serial_<serial>.lock.json`
- **Schema Compatibility**: Phải hỗ trợ đa dạng schema lock từ các repo khác nhau (`machine` hoặc `stt`, `project` hoặc `owner`, `serial` hoặc `device_id`, parse `machine_<N>` từ tên file). Không được phụ thuộc đơn lẻ vào `machine` / `project` để tránh hiển thị `[Máy None]` hay `unknown`.

## Behavior & Trigger Semantics
1. **Silent Watchdog**: When no active lock files (`machine_*.lock.json`) exist in `~/.codex/device-locks/`, the script produces output to console only and stays silent (does not spam empty notifications to Telegram).
2. **Alert on Active Locks**: When one or more locks are detected:
   - Formats a message listing each locked machine, owner project/PID, status, duration, and start time.
   - Highlights locks held over 90 minutes with `⚠️ (QUÁ HẠN > 90P)`.
   - Sends the report directly to Telegram group `-5518578446` via the bot token found in config/env.
3. **Phân biệt Transient Locks (Batch Execution) vs Triage Locks (`blocked`) vs Host Crash**:
   - Khi batch đa luồng (`multi-machine-feed-session`) đang chạy, watchdog quét thấy các máy ở trạng thái `running` hoặc `queued_v2`. Đây là **lock tiến trình bình thường**, máy chạy xong thành công sẽ **tự động nhả lock**.
   - **Lỗi UI Thật (Có Farm Alert & Banner Đỏ)**: Khi script gặp lỗi UI TikTok (popup kẹt, profile lỗi, v.v.), hệ thống bắn Farm Alert về Telegram và đánh dấu `blocked`, **giữ hiện trường 90 phút (TTL 5400s)** để operator debug màn hình.
   - **Lỗi Host / Script Crash (Không có hiện trường UI)**: Nếu lỗi xảy ra ở tầng preflight/host code trước khi thao tác UI hoặc PID chết bất đắc dĩ, **BẮT BUỘC nhả lock ngay lập tức** (cấm ngâm lock mù làm tê liệt farm).
   - **Watcher bị chặn khi máy còn giữ lock (`WATCH_EVENT_LOCK_TIMEOUT`)**: Watcher (`gan_proxy_fleet.py watch`) phát hiện sự kiện reconnect nhưng tuân thủ central lock. Nếu máy còn file lock cũ (`running` hoặc `blocked`), Watcher sẽ chờ 10s và bỏ qua, không tự cướp quyền gán proxy. Cần Reaper thu hồi hoặc mở khóa thủ công thì Watcher mới tiếp quản gán lại VPN.
   - **Mở rộng Farm Alert Full Ca Nuôi Acc**: Farm Alert và Banner Đỏ tự động giám sát toàn bộ ca nuôi acc, bao gồm cả Feed session, Follow hook failure và Upload hook failure.
   - **Quy tắc Upload Video đầu tiên (Video #1)**: Nick chưa đăng video nào (`Video Đã Đăng == 0` -> đăng video 1) tự động kích hoạt up Avatar (`ENSURE_AVATAR`) ngay sau khi post video thành công.
4. **Manual Trigger / On-Demand Check**:
   - To trigger an immediate check and report: execute `python C:\Users\Kibe\AppData\Local\hermes\scripts\watch_device_locks.py` or trigger the cron job `cronjob action='run', job_id='71c2a1b6268c'`.

## Dead-Owner & Expired Lock Lifecycle (Reaper)
- **Watchdog vs Reaper (Auto-Reap Preflight Pattern)**: 
  - Watchdog `watch_device_locks.py` được tích hợp sẵn bước gọi trực tiếp `reap-dead-owner-locks.py` (auto-reap preflight) ngay trước khi `scan_active_locks()`.
  - Điều này triệt tiêu hoàn toàn race-condition / lệch pha: mọi lock hết hạn (>90m TTL) hoặc dead-owner sẽ được thu hồi và đưa về Home ngay lập tức trước khi watchdog chụp snapshot báo cáo, đảm bảo báo cáo gửi về Telegram không bao giờ bị báo ảo.
  - Cron `device-locks-watchdog` được ghim ở mốc `1,16,31,46 * * * *` (ngay sau tick reaper `0,15,30,45`).
- **Universal Reaping & Expiration Policy (BẮT BUỘC)**:
  - **Trạng thái `blocked` (Giữ hiện trường / Triage)**: Giữ tối đa **90 phút (TTL 5400s)** kể từ `locked_at` / `created_at`. Quá 90 phút bắt buộc tự động thu hồi (reap vào quarantine) và đưa máy về Home.
  - **Tất cả các trạng thái khác (`running`, `handoff`, `recovery`, `failed_locked`, `temporarily_skipped`)**:
    - Nếu process owner đã chết (`owner_alive == False`): **Thu hồi ngay lập tức** (dọn orphan crash).
    - Nếu process owner còn sống (`owner_alive == True`): Giữ khi đang active, nhưng nếu tuổi lock vượt quá **90 phút (age >= 5400s)** tính từ thời điểm bắt đầu / chuyển trạng thái (`handoff_at` / `started_at`): **Thu hồi tự động theo timeout** để tránh kẹt vĩnh viễn khi process treo.
    - Nếu không xác minh được owner (`owner_alive is None`): Nếu quá 90 phút -> thu hồi tự động theo `unknown_expired`.
- **Timestamp Parsing Chuẩn Hóa theo Từng Status**:
  - `blocked`: Ưu tiên `locked_at` -> `created_at` -> `handoff_at` -> `started_at`.
  - `handoff`, `recovery`, `failed_locked`, `temporarily_skipped`: Ưu tiên `handoff_at` -> `locked_at` -> `started_at` -> `process_started_at` -> `created_at`.
  - `running`, `queued`, `queued_v2`: Ưu tiên `started_at` -> `process_started_at` -> `created_at`.
  - Fallback: `p.stat().st_mtime`.
  - Xử lý Timezone: Phân biệt rõ chuỗi có explicit offset (Z, +00:00, +07:00) với chuỗi naive ISO / strftime (bắt buộc mặc định gắn `VN_TZ = timezone(timedelta(hours=7))` trước khi chuyển về UTC) để không bao giờ bị lệch 7 giờ tính sai thời gian giữ lock.
  - Bắt lỗi triệt để: Bắt trọn `(ValueError, OSError, OverflowError, TypeError, Exception)` khi parse timestamp để không để crash toàn bộ vòng lặp reaper khi gặp file JSON lỗi.
- **Dọn Dẹp App & Thiết Bị Khi Thu Hồi Lock**:
  - Khi bất kỳ lock nào bị thu hồi (expired, timeout, hoặc dead owner), reaper gọi `_cleanup_device_screen(serial)`: chạy `am force-stop` cho cả `com.ss.android.ugc.trill` và `com.zhiliaoapp.musically`, sau đó bấm `input keyevent 3` đưa máy về Home.
  - Mỗi lệnh ADB phải nằm trong một khối `try-except` riêng biệt để lỗi timeout ở lệnh trước không làm nghẽn các lệnh cleanup phía sau.
- **Lưu Trữ Quarantine**: File thu hồi được chuyển vào quarantine `~/.codex/device-locks-reaped/<timestamp>/`, tuyệt đối không xóa cứng.
- **Cron Scheduling Discipline & Phase Alignment**:
  - Job `reap-dead-owner-locks` phải ghim cron 5 trường cố định (`*/15 * * * *`) thay vì `every 30m` interval để tránh tình trạng trôi tick (scheduler drift) qua đêm dẫn đến lock tích tụ.
  - **Tránh Báo Ảo "Quá Hạn Chưa Tự Unlock" (Watchdog / Reaper Race Condition)**: Nếu watchdog dùng interval `every 15m` lệch pha với reaper (ví dụ watchdog chạy lúc phút 56 còn reaper chạy lúc phút 00), watchdog có thể quét trúng thời điểm lock vừa chạm 124 phút (lúc 10:45 reaper chưa đủ 120m để dọn, đến 11:00 reaper mới dọn). Watchdog nên được set chạy ngay sau reaper (ví dụ `1,16,31,46 * * * *` hoặc `2,17,32,47 * * * *`) để reaper dọn sạch lock hết hạn trước khi watchdog quét báo cáo.
  - Khi điều tra "quá 2h chưa tự mở": Bắt buộc kiểm tra log/quarantine tại `~/.codex/device-locks-reaped/<timestamp>` để xem reaper đã dọn ở tick kế tiếp hay chưa trước khi kết luận reaper bị lỗi.
- **Cron Configuration & Scripts Synchronization**: Toàn bộ cấu hình cron chuẩn (`jobs.json`) và scripts thực thi (`scripts/*.py`) được quản lý tập trung trong repo `D:\Taadaa\Hermes\deploy\hermes-home\` để đồng bộ xuyên suốt các máy host (Kibe ↔ Admin). Không lưu lẻ tẻ cục bộ không track git.

## Unlock & Remediation Procedures
- **Mở khóa máy đơn lẻ**: Di chuyển cả `machine_<N>.lock.json` và `serial_<serial>.lock.json` tương ứng vào thư mục backup có timestamp `backup_user_unlock_<timestamp>`.
- **Mở khóa toàn bộ ("Unlock all" / "Mở khóa hết")**: Backup và dọn sạch toàn bộ `*.lock.json` trong `~/.codex/device-locks/` vào thư mục `backup_user_unlock_all_<timestamp>`.
- Tuyệt đối giữ đúng mã máy/serial, không để rơi vào tình trạng parse lỗi ra `Máy None`.
