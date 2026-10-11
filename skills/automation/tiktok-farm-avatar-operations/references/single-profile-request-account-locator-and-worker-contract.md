# Single-profile avatar request: locator and worker contract

Use this reference when an operator sends a TikTok Profile screenshot and says to change the avatar for that channel.

## Ground-truth lookup

1. Read the visible username from the screenshot; do not use the display name as the key.
2. Query `D:/Taadaa/data/tiktok_tracker.db` only for the exact username in `account_mapping` and `farm_account_info`.
3. Confirm the matching row in the relevant `D:/OneDrive/TaadaaData/<host>/Tik<N>.xlsx`, including `may`, username, device ID, `Folder Video`, `video gốc`, and the `Avatar` column.
4. Preserve the resolved tuple in the work report: `(username, may, tik, serial, host_id, folder_video, video_goc)`.

## State boundaries

- `avatar.jpg` written to both source/mirror paths means only that the source artifact is staged.
- `avatar_replace_queue.status = 'PENDING'` means the device upload is queued, not completed.
- A device inspection showing `Screen: OFF` or Launcher focus is field evidence that the machine is asleep/idle; it is not evidence that TikTok was opened or that the avatar changed.
- Keep the queue `PENDING` until the runner report and a fresh full Profile screenshot visibly confirm the target username and the new circular avatar.

## Worker dispatch contract

- Include exactly scoped `FILE: D:\Taadaa\...` paths on its OWN dedicated line with trailing newline (e.g. `FILE: D:\Taadaa\tmp\script.py\n`). CẤM viết liền câu hoặc có dấu chấm ngay sau đường dẫn (`FILE: D:\Taadaa\tmp\script.py. Target...`), vì regex parser của Worker Gate sẽ bốc toàn bộ phần mô tả phía sau thành tên file, gây lỗi `[WORKER GATE - SCOPE LOCK BREACH]`.
- Lưu ý ranh giới Worker Gate Whitelist & Terminal: Worker subagent bị giới hạn chặt trong whitelist `D:\Taadaa`, không thể truy cập trực tiếp `D:\video goc`, `D:\TIKTOK-videonuoinick`, hay `D:\OneDrive\TaadaaData` (`[WORKER GATE - OUT OF WHITELIST]`), và terminal của Worker chỉ được phép chạy: `git status/diff/log`, `adb devices`, `inspect_machine.py <N>`, `pytest`, `psutil`. Worker CẤM chạy arbitrary python scripts hay powershell.
- Khi cần cập nhật database, Excel, cắm cờ bảo vệ thủ công `.manual_avatar_locked` và kích hoạt launcher PowerShell: Coordinator viết một script tích hợp `D:\Taadaa\tmp\prepare_and_launch_avatar_<may>.py` và kích hoạt chạy nền qua `terminal(background=True, notify_on_complete=True, timeout=360)` để event-driven đánh thức.
- Include `FAIL_FAST:` with a concrete early-abort condition (for example, missing exact workbook row/schema or no suitable source frame within the first three iterations).
- State explicitly that the worker prepares/synchronizes files and queue state only; it must not touch the device or claim upload success.
- If the guard rejects the dispatch for a malformed contract, fix the contract rather than retrying the same prompt.

## Coordinator closeout

Before launching the canonical avatar-only runner, inspect the staged square image through the required visual gate. After the runner exits, verify the per-target report and full-screen Profile evidence. Report source sync, queue status, runner result, and visual verification as separate fields; never collapse them into “done.”
