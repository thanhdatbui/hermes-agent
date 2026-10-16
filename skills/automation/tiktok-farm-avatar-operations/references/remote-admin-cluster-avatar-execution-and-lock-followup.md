# Remote Admin Cluster Avatar Execution & Device-Lock Follow-up

## 1. Remote Admin Farm (Machines >= 200) Host Routing
- **Pitfall**: Running `run_avatar_batch_3accs.py` or `run_tiktok_upload_avatar.ps1` locally on host `Kibe` for machines in the Admin range (`>= 200`, e.g., Máy 201) will fail with:
  `[DEVICE_OFFLINE] device is offline or ADB/USB disconnected for <serial>: adb.exe: device '<serial>' not found`.
- **Root Cause**: Devices in range `[200, 999]` are physically attached to the Admin host (`192.168.110.119:5037`). The local PowerShell launcher invokes local `adb.exe` without `-H 192.168.110.119 -P 5037`.
- **Rule & Invariant**:
  - Always execute avatar operations for Admin machines directly on `admin-farm` via SSH:
    ```bash
    python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>"
    ```
  - Or trigger the PowerShell launcher remotely on Admin host with `echo RUN`.

## 2. Anti-Stall / Anti-Idle Follow-up on Locked Devices (Chống Bỏ Quên Khi Kẹt Lock)
- **User Frustration Signal**: "Tại sao tao phải nhắc mày mới làm?"
- **Problem**: When a device is locked by an ongoing batch (e.g. `multi-machine-feed-session` holding `machine_<M>.lock.json`), the agent reports `SKIPPED_LOCKED` and then goes idle, waiting for the user to prompt hours later.
- **Rule**:
  - **NEVER go silent/idle** after encountering a device lock without an active watchdog, cronjob, or background waiter.
  - When a device is locked:
    1. Check lock owner PID and process status (`psutil.pid_exists(pid)`).
    2. If the lock is active, schedule an event-driven check or notify-on-complete background task/cron to re-attempt immediately once the feed session finishes (typically 30-60m).
    3. State clearly to the user: "Tiến trình sẽ tự động kích hoạt lại ngay khi lock được giải phóng; Agent chủ động bám sát không cần user nhắc".
