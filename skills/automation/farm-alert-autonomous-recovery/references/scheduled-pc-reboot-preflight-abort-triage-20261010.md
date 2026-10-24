# Triage Cảnh Báo Cron farm-scheduled-pc-reboot (Preflight Abort vs Crash)

## Hiện Tượng & Nguyên Nhân Gốc
Khi nhận alert từ Hermes Cron:
`⚠️ Cron 'farm-scheduled-pc-reboot' failed: Script exited with code 2 stdout: === [FARM REBOOT COORDINATOR] ... [ABORT] Phát hiện N tiến trình automation quan trọng đang chạy...`

Đây **KHÔNG PHẢI lỗi crash** mà là **Safety Preflight Abort có chủ đích**:
1. Script `farm_scheduled_reboot.py` (chạy 04:45 sáng Thứ 2, 4, 7) có preflight guard quét các keyword tiến trình automation (`CRITICAL_AUTOMATION_KEYWORDS` gồm `tiktok_workflow`, `multi_machine_feed_session`, `run_tiktok.py`, `clear_tiktok_cache`,...).
2. Nếu phát hiện có tiến trình nuôi/avatar/cache đang chạy trong khoảng Dead Zone, script chủ động abort với `exit code 2` (hoặc `code 3` nếu có device-lock active) để tránh reboot làm hỏng phiên.
3. Vì cron job đặt `no_agent: true`, scheduler coi exit code != 0 là failure và đẩy alert về Telegram.

## Quy Trình Xử Lý T0 Hiện Trường
1. **Kiểm tra persistent audit log O(1):**
   - Đọc bản ghi cuối cùng tại `D:\Taadaa\runtime\kibe\logs\farm_reboot.jsonl`.
   - Lấy `correlation_id`, `metrics.active_processes_count`, danh sách tiến trình và PID.
2. **Kiểm tra tiến trình live & device locks:**
   - Dùng lệnh python kiểm tra psutil với timeout (bắt buộc `timeout <= 60s` để tránh `GUARD_FOREGROUND_TIMEOUT_MISSING`).
   - Kiểm tra `~/.codex/device-locks` để xác nhận không có lock mồ côi.
3. **Phân định & Báo cáo:**
   - Nếu các tiến trình là hợp lệ (ví dụ: batch upload avatar ban đêm `post-evening-avatar-watchdog`), báo cáo rõ ràng đây là **Safety Abort có chủ đích / False Alarm sự cố**.
   - Tuyệt đối KHÔNG ép reboot (`--force` / `--force-unsafe`) khi tiến trình đang chạy. Để batch tự nhiên hoàn tất trước Ca 1 (06:00).
