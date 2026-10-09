# Clean Skip on Device Lock (TikTok Feed Session)

## Bối cảnh
Khi chạy ca nuôi TikTok (`run-feed-session.ps1` hoặc `multi-machine-feed-session`), một số máy có thể đang bị giữ lock bởi operator/quy trình khác (ví dụ: đang reg nick, login, recovery qua `.codex\device-locks\machine_<N>.lock.json`).

## Cơ chế xử lý 2 tầng (Updated 2026-09-17)

### 1. Tầng Pre-flight: `scripts/run-feed-session.ps1`
- Vòng lặp tiền kiểm tra lock quét danh sách máy đầu vào:
  - Nếu lock tồn tại và process (`$proc`) còn sống:
    - Ghi log `[PRE-FLIGHT] SKIP may $m: dang bi lock boi PID <pid> (project=<project>). Bo qua may nay khoi ca nuoi.`
    - KHÔNG thêm máy vào `$activeMachineValues`.
  - Nếu lock stale (`$proc` đã chết):
    - Tự động xóa file lock stale và tiếp tục đưa máy vào `$activeMachineValues`.
  - Nếu không có lock (hoặc lỗi đọc):
    - Đưa máy vào `$activeMachineValues`.
- Sau vòng lặp:
  - Nếu `$activeMachineValues.Count -eq 0`: in thông báo clean exit `exit 0` (không báo lỗi).
  - Cập nhật `$machineList = ($activeMachineValues -join ",")` để truyền vào `run_tiktok.py`.

### 2. Tầng Tổng hợp kết quả: `python_runner/flows/multi_machine_feed_session.py` (`_aggregate_rows`)
- Trường hợp 100% máy bị lock (`final_statuses == {"skipped-device-locked"}`):
  - Trả về `ExitStatus.MANUAL_NEEDED`, `final_status = "manual-needed"`.
- Trường hợp Partial Skip (`"skipped-device-locked"` cùng các máy khác):
  - Nếu có máy thành công hoặc degraded (`has_success = True`):
    - Trả về `ExitStatus.SUCCESS`, `final_status = "success"`, thông báo `"multi-machine-feed-session completed with some locked machines cleanly skipped"`.
    - Tránh báo false alarm / manual-needed khi phần còn lại của ca nuôi hoàn tất bình thường.
  - Nếu không có máy nào thành công/degraded:
    - Trả về `ExitStatus.MANUAL_NEEDED`.
