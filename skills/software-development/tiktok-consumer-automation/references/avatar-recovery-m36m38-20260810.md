# Avatar recovery m36 + m38 (2026-08-10, full-pipeline observation)

Session detail cho "Avatar recovery chạy FULL media pipeline" (SKILL.md). Repo
`D:\Taadaa\Tiktok-video` HEAD f58a425 (child ccd28f3 = avatar picker album fix,
43e1825 = reboot kwarg fix), venv-core024 automation-core 0.4.40.

## Target + mục tiêu

- m36 serial `ce10160ac8f1962305`, m38 serial `ce06160685310f1c04`.
- Cả 2 report mới nhất đều `MANUAL_REVIEW` avatar FINAL_BLOCKED, `post_verified=true`,
  `post_submission_state=ACCEPTED` → chỉ retry avatar với
  `--force-avatar-upload --force-avatar-machines N`, KHÔNG retry post.
  - m36 (17:50): `[AVATAR_UPLOAD_MENU_MISSING] Không tìm thấy Tải ảnh lên`.
  - m38 (17:57): `[AVATAR_PICKER_NO_MATCH] best=0.465`.

## Lock archive

- 4 alias `machine_36/serial_ce10160…/machine_38/serial_ce061606…` đều
  `status=handoff`, `owner_active=false`, PID 15484 + 74036 dead (WMIC "No
  Instance(s) Available" + `tasklist /FI "PID eq X" /NH` "No tasks").
- Archive guard script `D:\CodexRuntime\tiktok-video\_avatar_archive_m36m38.py`:
  re-read 4 alias ngay trước khi move → verify fields + pid_dead + competitor
  scan (Name-filter python) → copy vào
  `C:\Users\Kibe\.codex\device-locks\backup_avatar_recovery_m36m38_20260810_182521\`
  + `evidence.json` → verify archive đúng 4 file → mới xóa live aliases.

## Worker + lệnh

```
echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" \
  "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow \
  --config "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" --machine N \
  --no-dry-run --recovery-mode --allow-device-reboot-recovery \
  --force-avatar-upload --force-avatar-machines N \
  > /d/CodexRuntime/tiktok-video/avatar-recovery-v4-mN-<ts>.log 2>&1; echo WORKER_EXIT=$?
```

- 1 process nền độc lập/máy (parallel ≤2), log riêng:
  `avatar-recovery-v4-m36-20260810_183132.log`, `avatar-recovery-v4-m38-20260810_183209.log`.
- Cả 2 log có dòng chuẩn: `Target binding: workbook row machine=N serial=…; effective config rebound to this row`.
- Guard trước launch: probe venv `reboot_and_restore` params (pass — có
  `wait_for_proxy_ready_after_reboot`), import tiktok_workflow từ venv OK (dùng
  `env -u PYTHONPATH -u PYTHONHOME` để tránh resolve nhầm hermes venv).

## Ladder thực tế xuất hiện (cả 2 máy)

- B1 ATX-kill: KHÔNG có marker — startup sạch, không lỗi uiautomator.
- B2: `[OPEN_TIKTOK] Force-stop + relaunch 1/2` (bounded startup, không phải
  ladder relaunch 2/2).
- B3 soft reboot: KHÔNG chạy (feed vào nhanh, proxy ready từ đầu).
- Feed: `[WAIT_FEED] Root surface confirmed with indicator: 'đề xuất'/'trang chủ'`.
- Account: `[ACCOUNT_SWITCHER] Target account already selected; skipping switcher ✓`.

## Diễn biến quan trọng

- **m36**: receipt `machine_36_video_12.json` = `verification_pending` + ACCEPTED →
  worker resolve video 12, push media (codex_36_12), đi VIDEO_PICK/CAPTION_FILL
  nhưng barrier finalize: `Workbook updated: Video Đã Đăng = 12` không tap Post
  thật → ENSURE_AVATAR.
- **m38**: ALL receipts 1-15 `completed` + ACCEPTED. Worker vẫn re-resolve
  `Reserved SHA-256=92caccd… for machine=38 video=15` — SHA TRÙNG `media_sha256`
  của receipt video 15 `completed` → rồi log `New composer confirmed; tapped exact
  post button text` → **NGHI REPOST video 15**. Chưa xác minh report cuối khi kết
  thúc session (worker còn chạy VERIFY_POST) → báo INCOMPLETE_PENDING_WORKER,
  không phóng worker mới, đọc report cuối (`post_verified`, `post_submission_state`,
  tile profile) + receipt mới trước khi kết luận.

## Avatar kết quả

- **m36**: picker MATCH — `[ENSURE_AVATAR] Download không hiện; giữ Recent grid và
  verify từng tile bằng similarity source` → `Visual picker match corr=0.601 tại
  (0,345,263,611)` → `Picker tile 1/1 similarity=0.601 threshold=0.600` (album fix
  ccd28f3 hoạt động — hết AVATAR_PICKER_NO_MATCH). NHƯNG verify sau save FAIL:
  `Avatar source similarity=-0.034, threshold=0.800` + `Avatar crop entropy=1.83,
  threshold=4.00` (7 poll/30s) → `[ENSURE_AVATAR] FINAL_BLOCKED; post_verified=True`
  → `MANUAL_REVIEW`, lock giữ handoff. Report:
  `D:\CodexRuntime\tiktok-video\runs\run_ce10160ac8f1962305_20260810_183133\report.json`.
  Entropy thấp = crop rỗng (save chưa commit / tap save miss) — cần user soi ảnh
  máy thật. KHÔNG sửa ngưỡng correlation.
- **m38**: chưa tới ENSURE_AVATAR khi session cắt (đang VERIFY_POST).

## Bài học (đã ghi vào SKILL.md)

1. `--force-avatar-upload` KHÔNG bypass pipeline media/post — barrier receipt mới
   là chốt chặn repost; đọc receipt mới nhất trước launch để biết video resolve
   là verification_pending (kỳ vọng) hay completed (cờ đỏ).
2. Verified SHA fingerprint log vs `media_sha256` receipt để phát hiện re-resolve
   video đã completed.
3. Post-save verify entropy thấp = crop rỗng (save miss), ≠ m74 correlation
   false-negative. Báo user soi máy.
4. WMIC CommandLine-like tự-match shell wrapper → lọc Name='python.exe' trước.
5. search_files lỗi trên drive D: host này → grep -rn qua terminal.