# Exhaustive Avatar Dedup and Cron Handoff Discipline

## 1. Complete Hash Scan vs. Hardcoded Assumptions
- Never rely on hardcoded duplicate lists (`FOLDERS_DUP`) or past session claims of "all duplicates resolved".
- When tasked with verifying avatar uniqueness across the farm:
  1. Scan all existing numeric folders in both `D:\TIKTOK-videonuoinick` and `D:\video goc`.
  2. Compute full MD5/SHA-256 hashes of every `avatar.jpg`.
  3. Group folders strictly by hash collisions.
  4. Only declare success when both roots report `Dups: 0` in an exhaustive re-scan.

## 2. Collision-Free Regeneration from Source Videos
- In any duplicate group, designate the lowest-numbered folder as canonical and keep its avatar.
- Regenerate unique avatars for all other members in the collision group from videos in their own folders:
  - Do not default to `videos[0]` at `t = 0s`. Shared channels or intros cause identical initial frames.
  - Apply folder-dependent video rotation: `shift = (folder * 7 + 13) % len(videos)` and seek timestamps `t = 3s..11s`.
  - Check candidate hash against the global `known_hashes` set before saving. If collision persists, increment seek/index or use YOLO/face content-aware detection (`make_avatar_yolo.py`).
  - Once unique, write/copy synchronously to both `D:\video goc\<folder>\avatar.jpg` and `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`.

## 3. Safe Enrollment into Watchdog Cron Queue
- Do not guess `tik` or `username` via folder arithmetic if authoritative workbooks exist (`taikhoan_run_safe.xlsx`, `Tik1.xlsx`..`Tik8.xlsx`, `taikhoan_dat_v2_updated .xlsx`).
- Map each regenerated folder to `(username, may, tik, host_id, folder_video)`.
- Enroll accounts into the canonical watchdog table:
  ```sql
  INSERT OR REPLACE INTO avatar_replace_queue (username, may, tik, host_id, folder_video, status)
  VALUES (?, ?, ?, ?, ?, 'PENDING');
  ```
- Trigger or verify the background cron runner (`post_evening_avatar_watchdog.py`) so pending accounts are automatically processed without post-video uploads (`-AvatarOnly`).

## 4. Execution Discipline & User Steering
- When the user directs execution ("làm đi", "chạy đi"), run the canonical local scripts/runners directly. Do not route live operations to third-party tools like Claude CLI unless explicitly told to review or fix guard mechanisms.
- Do not stop to ask routine questions after an execution directive.
- If an account switcher fails, follow `automation-core` invariants (scroll/sticky profile header then tap profile name/ID; never tap avatar circle).
