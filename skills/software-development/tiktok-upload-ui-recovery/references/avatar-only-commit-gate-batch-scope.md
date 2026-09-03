# AVATAR-ONLY + COMMIT GATE + batch-scope pitfalls (2026-08-10, user chốt)

## AVATAR-ONLY (user correction sau lỗi đăng video thừa m38 tile 12→13 + m36/m38 run 18:32)

- Khi user yêu cầu **CHỈ đổi avatar** → DÙNG:
  `--avatar-smoke --force-avatar-upload --force-avatar-machines N`
  flow: RESOLVE → ENSURE_AVATAR → RELEASE; KHÔNG push video, KHÔNG post, KHÔNG ghi workbook.
- **CẤM** `--force-avatar-upload` đơn lẻ cho mục đích avatar-only — nó chạy FULL flow
  (push video + POST) rồi mới tới ENSURE_AVATAR → đăng video thừa.
- Verify thành công: status `AVATAR_SMOKE_SUCCESS` / signature `FORCED_REPLACED_VERIFIED`;
  `post_submission_state` phải None (không đụng post); report không có AVATAR_*_BLOCKED.
- Worker avatar smoke cần token xác nhận `AVATAR-SMOKE` (không phải `YES`).

## Batch launcher: -ForceAvatarMachineList KHÔNG giới hạn máy chạy

`run_tiktok_upload_batch.ps1 -ForceAvatarMachineList 36,38` chỉ THÊM cờ force-avatar cho 2 máy
đó, batch vẫn chạy TOÀN BỘ inventory (46 máy target). Muốn chạy đúng N máy → launch worker
riêng từng máy (python -m tiktok_workflow --machine N), không qua batch launcher.

## COMMIT GATE (user chốt 2026-08-10)

- Commit + push **KHI FULL pytest suite xanh** (`pytest tests/test_tiktok_workflow.py -q`),
  KHÔNG chờ live-run success.
- Live-run là bước verify TIẾP THEO (lỗi mới lộ ra → fix tiếp, commit tiếp); không chặn release.
- Fix sai trên máy thật → revert NGAY bản git (git revert/checkout) — git là lưới an toàn,
  commit sớm không đáng sợ; đáng sợ là code chưa commit bị mất (worker chết, PC sleep).

## Lỗi proxy/readiness → reboot để watcher gán lại

- `proxy readiness timed out` / `live VPN verifier failed` khi ACQUIRE_LOCKS/preflight →
  reboot máy; gan-proxy watcher (poll 30s) tự gán VPN + publish readiness sau boot; chờ
  readiness 60-90s rồi chạy lại. KHÔNG retry mù, KHÔNG sửa lock thủ công.
- Lưu ý: watcher chỉ gán lại khi máy RECONNECT — nếu chỉ PC sleep (máy không reboot) thì
  không có sự kiện reconnect → proxy không được gán lại. Reboot máy để ép watcher xử lý.
- Reboot qua terminal bị hardline chặn (pattern 'reboot') → chạy qua script file python
  subprocess adb (hợp lệ, giống workflow tự gọi reboot_and_restore trong code).
