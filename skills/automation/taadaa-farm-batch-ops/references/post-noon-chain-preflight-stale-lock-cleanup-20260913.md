# Preflight Chuỗi Sau Ca Trưa: Xác Minh Feed-Ended + Dọn Stale Blocked Locks (13/09/2026)

## Vấn đề
`post_noon_chain_watchdog.py::has_active_device_locks()` coi mọi file lock có
`status` trong (`active`, `running`, `queued`, `blocked`) là bận → return 0 im lặng,
chuỗi Reg Gmail → Add 2FA TikTok không bao giờ kích hoạt. Thực tế 13/09/2026:
feed runner PID 80284 đã chết nhưng để lại 6 file `machine_*.lock.json` +
`serial_*.lock.json` với `status: "blocked"` → watchdog kẹt vĩnh viễn dù farm đã rảnh.

## Preflight O(1) trước khi `--force` (đã chạy thật 13/09/2026)
1. PID trong lock còn sống không: `tasklist /FI "PID eq <pid>"` + `psutil.pid_exists(pid)`.
2. Không còn feed runner thật: `Get-CimInstance Win32_Process` lọc CommandLine
   `*run_tiktok*` / `*multi_machine*` / `*feed-session*` → 0 kết quả
   (loại trừ chính câu lệnh query bash/powershell chứa chuỗi tìm kiếm).
3. Ca 2 đã xong: `feed_session_reported.json` có `<today>_ca2_phien2`;
   `.ai-runs/<mới nhất>/summary.txt` có `final_status == success`.
4. Locks: liệt kê `~/.codex/device-locks/machine_*.lock.json` +
   `serial_*.lock.json`, đọc `pid` + `status` từng file; file nào PID đã chết → xóa.
   GIỮ NGUYÊN `reg_daily_cooldowns.json` (cooldown reg theo ngày, không phải lock máy).
5. Chạy thật (không dry-run): `python .../post_noon_chain_watchdog.py --force`,
   thu toàn bộ stdout/stderr + exit code từng Phase, đối soát artifact trên đĩa
   (`logs_parallel_*` của Reg Gmail, output `run_batch_live_2fa.py`,
   `post_noon_chain_state.json`) trước khi báo cáo.

## Quy tắc điều phối
- Coordinator dọn stale lock của PID chết TRƯỚC khi dispatch worker chạy `--force`;
  worker chỉ chạy đúng contract, không tự dọn lock ngoài scope.
- CẤM dispatch `--force` khi feed runner còn sống hoặc lock của PID đang chạy
  còn hiệu lực (tranh chấp UI TikTok giữa feed session và batch reg/2FA).
