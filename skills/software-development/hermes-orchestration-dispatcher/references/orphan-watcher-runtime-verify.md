# Runtime verify: schedule-recovery-watch orphan cleanup (2026-08-06)

Context: Codex patch `run-schedule-recovery-watch.ps1` thêm `Assert-ExistingLeaseCanBeReplaced`
+ `Stop-ExistingOrphanedChild` để dọn orphan child khi parent chết, fail-closed khi parent
còn sống/binding sai. Patch chỉ verify offline (PowerShell parse, `git diff --check`, tests)
— **chưa ai xác nhận bằng runtime thật**. Session này hoàn tất phần còn thiếu.

## Quy trình verify runtime (4 bước)

### 1. Đọc hiện trạng trước khi đụng gì
- `git status`/`git diff --stat` cả 2 repo (consumer + automation-core) — biết Codex sửa gì.
- `schtasks /query /fo CSV | grep -i -E "tiktok|recovery|health"` — trạng thái task.
- Đọc lease file: `python_runner/runs/schedule-recovery-watch-lease.json`.
- **Quan trọng**: `tasklist //FI "PID eq N"` trong git-bash CÓ THỂ trả trống dù process sống
  (filter lỗi qua MSYS). Cross-check bằng `wmic process where "ProcessId=N" get ProcessId,CommandLine`
  hoặc `Get-CimInstance Win32_Process` — đừng kết luận "chết" chỉ từ tasklist.

### 2. Verify identity-match READ-ONLY trước bất kỳ side effect nào
Mirror chính xác logic `Test-ExistingChildIdentity -AllowOrphanedParent` của wrapper bằng script
độc lập (xem `scripts/verify-orphan-identity.ps1` trong skill này — bản dùng được, chỉ sửa path):
- Lease fields + binding fields đầy đủ; `binding.parent_pid == lease.pid`; `lease.parent_pid == lease.pid`.
- `binding.schema == 'tiktok-schedule-recovery-child-binding-v1'`; `binding.module == 'scheduler.recovery_runtime'`.
- `binding.lease_id/worker_session_id/child_pid/child_process_start_time/parent_process_start_time`
  khớp lease; `command_identity` khớp `child_command_identity`; repo_root/lease_path khớp.
- Process thật: start time khớp `child_process_start_time` (toàn bộ chuỗi, ToUniversalTime),
  ExecutablePath khớp `command_identity` (GetFullPath), ParentProcessId khớp `lease.pid`.
- Command line khớp TỪNG argument: `-m scheduler.recovery_runtime`, `--watch-lease <path>`,
  `--watch-lease-id <id>`, `--watch-parent-pid <pid>`, `--watch`, repo_root trong command line.
- **Parent dead + child alive + toàn bộ match = orphan hợp lệ → patch sẽ dọn đúng.**
- Parent alive hoặc bất kỳ field lệch = fail-closed (patch từ chối) — đúng thiết kế.

### 3. Trigger task + confirm side effect
- Backup lease trước: `cp lease.json lease.json.pre-orphan-clean-$(date +%Y%m%d-%H%M%S)`.
- `schtasks /run /tn "TikTokScheduleRecovery"` → SUCCESS.
- Sau ~20-40s: kiểm tra (a) child orphan PID biến mất (wmic), (b) lease file mới (lease_id mới,
  parent/child PID mới, state=running, heartbeat liên tục 15s), (c) activation marker mới,
  (d) log `runs/schedule-recovery-task.log` ghi liên tục.

### 4. Prove fail-closed (không double-run)
- Trigger task LẦN 2 khi watcher mới còn sống → phải bị từ chối:
  `schtasks /run` trả "currently running" + LastResult `-2147020576` (0x800710E0).
- Watcher cũ KHÔNG bị kill nhầm; lease không bị rotate.

## Kết quả session này (chuẩn so sánh)
- Orphan: parent 2476 dead, child 52164 alive, identity match 100% → patch dọn sạch.
- Watcher mới: parent 38128 + child 17228, lease `470736a3...`, heartbeat 15s đều.
- Trigger lần 2 bị từ chối `-2147020576` — fail-closed đúng.
- Task `TikTokScheduleRecovery`: Enabled + Running; `TikTokScheduleRecoveryHealth`: Ready.

## Pitfall
- Đừng tin report "live chưa chạy" của Codex — nó dừng ở offline verify; runtime confirm là việc
  coordinator/session làm sau (như session này).
- `-2147020576` = 0x800710E0 = task đang chạy (SCHED_S_TASK_RUNNING) — KHÔNG phải lỗi.
- Task action KHÔNG truyền `-ReplaceExisting` nhưng wrapper dòng `Assert-ExistingLeaseCanBeReplaced
  -Lease $existing ... -ReplaceExisting` luôn true → fail-closed vẫn giữ (parent sống → throw).
