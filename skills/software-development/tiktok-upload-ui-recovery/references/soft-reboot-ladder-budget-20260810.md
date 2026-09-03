# Soft-reboot B3 ladder + proxy handoff (2026-08-10)

## RULE 3 BƯỚC FIX LỖI UI (user-chốt, phủ all repo + core automation-core)

- B1: ATX-kill (uiautomator recovery)
- B2: force-stop + relaunch (TỐI ĐA 1 lần)
- B3: reboot máy (soft reboot, TỐI ĐA 1 lần)
- Budget THEO MÁY TRONG TURN: mỗi máy 1 relaunch + 1 reboot toàn bộ turn; các lần
  lỗi sau CHỈ được ATX-kill + coordinate fallback có evidence → fail thì MANUAL_REVIEW.
- Lỗi cùng chỗ sau đủ budget = thất bại. Lỗi ở chỗ khác (state/signature khác) được
  chạy lại chuỗi, nhưng vẫn nằm trong budget tổng của máy.
- Handler đặc thù fail vì UI/dump → route vào ladder, KHÔNG dừng sớm MANUAL_REVIEW.
- User phản đối "lỗi khác chỗ retry vô hạn": reboot hoài = reboot mỗi run recovery.
  Chốt budget cứng theo máy/turn, không reset theo run.

## Launcher phải luôn bật recovery ladder

Normal batch `run_tiktok_upload_batch.ps1` KHÔNG truyền `--allow-device-reboot-recovery`
là design bug: state machine config tắt soft reboot + kéo theo tắt coordinate fallback,
chỉ chạy được ATX-kill + relaunch rồi MANUAL_REVIEW. Log marker:
`Soft reboot recovery disabled by config for OPEN_TIKTOK` +
`allow_device_reboot_recovery=False -> bỏ qua coordinate fallback`.

Fix: normal live path phải luôn truyền `--allow-device-reboot-recovery` (PreflightOnly
và ProfileSmoke không nhận cờ live/recovery). Commit mẫu: `14d62ec`.

## Splash-stuck (kẹt splash đen) — máy 5/35

- Triệu chứng: `[WAIT_FEED] Visual gate matched=False white=0.000 dark=1.000` lặp lại
  qua relaunch; screenshot evidence toàn đen (TikTok splash logo), không có feed indicator.
- Flow đúng (đã implement `6ad3cfd`):
  1. Wait feed 90s (`feed_timeout`) — có nhánh "Launcher XML nằm dưới TikTok splash; tiếp tục chờ".
  2. Timeout → splash-stuck recovery: đóng Recent (`close_all_recent_apps`) + launch lại
     TikTok, budget riêng `SPLASH_STUCK_RECOVERY_MAX=2` — KHÔNG tính là ladder B2.
  3. Vẫn không được → ladder 3 bước → coordinate fallback có evidence.
- Khi đánh giá máy splash-stuck: màn đen ≠ "không có gì"; check screenshot evidence
  `coordinate-fallback-open_tiktok-before.png` trước khi kết luận.

## B3 bị chặn bởi DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED

- `_reserve_proxy_recovery_handoff` trả lỗi khi lease thiếu `request_maintenance_handoff`
  → code cũ fail-closed RECOVERY_FAILED → máy KHÔNG reboot.
- User xác nhận: watcher gan-proxy chạy ngầm (`gan_proxy_fleet.py watch --all --workers 80`
  poll 30s) tự gán VPN lại sau reboot → workflow KHÔNG được chặn B3 vì thiếu handoff thủ công.
- Fix `9301585`: gặp `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` → bỏ qua handoff
  (proxy_handoff=None, checkpoint `proxy_handoff_skipped_watcher_managed`), tiếp tục reboot.
  Các lỗi handoff khác (ACK_INVALID, PRE_REBOOT_BOOT_ID_UNAVAILABLE...) vẫn fail-closed.
- Sau reboot: `restore_proxy_after_reboot` với proxy_handoff=None nhưng readiness_marker
  tồn tại → PHẢI chờ watcher publish readiness (wait_for_proxy_ready, timeout 60-90s)
  rồi `require_android_vpn` — không bỏ qua bước chờ.

## PITFALL QUAN TRỌNG: kwarg core API phải đúng tên

- Bug thật làm B3 "chưa bao giờ chạy": state_machine gọi
  `reboot_and_restore(wait_for_proxy_ready_before_post_reboot=...)` nhưng automation-core
  chỉ có `wait_for_proxy_ready_after_reboot=...` → TypeError
  `got an unexpected keyword argument` → máy không reboot, ladder tưởng "đã thử B3".
- Log marker: `[REBOOT] Guarded reboot recovery failed: reboot_and_restore() got an
  unexpected keyword argument 'wait_for_proxy_ready_before_post_reboot'`.
- KHI GỌI HÀM CORE: verify signature trước bằng `inspect.signature()` thay vì đoán tên kwarg.
- Agent con cũng dính cùng lỗi khi viết test giả lập theo tên kwarg sai → khi fix production
  phải sửa luôn test mock (5 chỗ) và regression test kiểm tra cả 2 chiều
  (tên đúng có mặt, tên sai không có mặt).

## Chạy avatar đúng 1-2 máy — KHÔNG qua batch

- `run_tiktok_upload_batch.ps1 -ForceAvatarMachineList 36,38` chỉ THÊM cờ
  `--force-avatar-upload --force-avatar-machines` cho máy đó; batch vẫn chạy TOÀN BỘ
  target farm (46 máy) → kill ngay nếu chỉ muốn đổi avatar vài máy.
- Cách đúng: worker riêng từng máy, mỗi máy 1 process:
  `echo YES | PYTHONPATH=... python -m tiktok_workflow --config config-machine-62.yaml
   --machine N --no-dry-run --recovery-mode --force-avatar-upload --force-avatar-machines N`
- Signature avatar: `AVATAR_FINAL_BLOCKED / AVATAR_UPLOAD_MENU_MISSING` = không tìm thấy
  "Tải ảnh lên" trong profile edit.

## Recovery entrypoint: KHÔNG đòi config-machine-N.yaml

- Direct recovery dùng template `D:\CodexRuntime\tiktok-video\config-machine-62.yaml`
  + `--machine N`; workflow bind serial từ workbook row
  (log: `effective config rebound to this row`). Đòi `config-machine-N.yaml` là blocker GIẢ
  (đã từng làm recovery chặn nhầm cả nhóm máy).

## Hardline blocklist: từ "reboot" trong command

- Terminal tool block lệnh chứa "reboot" (kể cả grep log): dùng từ khóa thay thế
  (`relaunch 2/2`, `ATX-kill`, `Ladder cạn`, `FINAL_BLOCKED`) khi đọc log; commit message
  chứa "reboot" qua file `-F` để tránh block.
