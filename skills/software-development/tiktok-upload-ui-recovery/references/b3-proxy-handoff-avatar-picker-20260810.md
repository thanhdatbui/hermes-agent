# B3 soft-reboot proxy handoff + splash-stuck + avatar picker (2026-08-10)

Session evidence: batch all-Tik1 + recovery v2/v3/v4 (máy 5/27/35/70/34), avatar m36/m38.
Repo D:\Taadaa\Tiktok-video; automation-core là d:/Taadaa/automation-core.

## 1. B3 soft reboot — 2 lỗi đã gặp và fix

### 1a. Kwarg sai tên core API → reboot chưa từng chạy (silent TypeError)
- Commit `9301585` gọi `reboot_and_restore(wait_for_proxy_ready_before_post_reboot=...)` nhưng
  automation-core thật chỉ có `wait_for_proxy_ready_after_reboot=...`.
- Hậu quả: log `[REBOOT] Guarded reboot recovery failed: got an unexpected keyword argument`
  → máy KHÔNG reboot, ladder xuất hiện như "đã thử" nhưng thực tế B3 chưa bao giờ chạy.
- Fix: `43e1825` đổi đúng tên kwarg + regression test
  `test_soft_reboot_calls_core_with_correct_proxy_kwarg` đọc source state_machine.py và assert
  tên kwarg đúng (`wait_for_proxy_ready_after_reboot`) + tên sai vắng mặt.
- PITFALL: TRƯỚC khi wire callback vào core, verify signature bằng:
  `python -c "import inspect, automation_core; print(inspect.signature(automation_core.reboot_and_restore))"`
  Không đoán tên kwarg từ tên biến local.

### 1b. DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED chặn reboot
- `_reserve_proxy_recovery_handoff()` trả `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` khi
  device_lease thiếu `request_maintenance_handoff` → code cũ fail-closed RECOVERY_FAILED,
  máy không reboot dù watcher gan-proxy đang chạy ngầm (gan_proxy_fleet.py watch --all --workers 80).
- Theo user: "lỗi TikTok thì reboot xong watcher gán VPN làm tiếp" → handoff thủ công KHÔNG cần
  khi watcher self-managed. Fix (`9301585`): UNSUPPORTED → bỏ qua handoff (proxy_handoff=None),
  tiếp tục reboot; ghi checkpoint reason `proxy_handoff_skipped_watcher_managed`.
- Sau reboot với proxy_handoff=None + readiness_marker còn tồn tại: VẪN phải chờ watcher publish
  readiness (`wait_for_proxy_ready` với post_boot_id, timeout 60-90s, poll 30s) rồi `require_android_vpn`
  — không bỏ qua bước chờ. Các lỗi handoff khác (ACK_INVALID, PRE_REBOOT_BOOT_ID_UNAVAILABLE...)
  vẫn fail-closed.

## 2. Splash-stuck flow (user-chốt thứ tự)
Máy 5/35: kẹt splash đen (visual gate `white=0.000 dark=1.000`), coordinate fallback không có target.
Flow đúng:
1. Wait feed (feed_timeout 90s) — có nhánh "Launcher XML dưới TikTok splash; tiếp tục chờ".
2. Timeout ở splash → splash-stuck recovery: close recent apps + relaunch TikTok,
   KHÔNG tính là ladder B2 (budget riêng SPLASH_STUCK_RECOVERY_MAX=2; checkpoint `splash_stuck_recovery_used`).
3. Vẫn không được → ladder B1 ATX-kill → B2 force-stop+relaunch (1 lần) → B3 soft reboot (1 lần) → coordinate fallback.

## 3. Rule 3 bước UI — budget chốt (phủ all repo + core)
- B1 ATX-kill → B2 force-stop+relaunch (TỐI ĐA 1) → B3 reboot máy (TỐI ĐA 1).
- Budget theo MÁY trong turn chạy: mỗi máy chỉ 1 relaunch + 1 reboot toàn turn;
  sau đó mọi lần lỗi chỉ ATX-kill + coordinate fallback có evidence → fail thì MANUAL_REVIEW.
- Lỗi CÙNG CHỖ sau đủ budget = thất bại. Lỗi KHÁC CHỖ (state/signature khác) được chạy lại chuỗi
  nhưng vẫn trong budget tổng của máy.
- Handler đặc thù fail vì UI/dump (VIDEO_PICK_SHOP_REPLAY_CARD recapture, DISMISS_POPUPS
  uiautomator_idle_state_error) PHẢI route vào ladder, không dừng sớm MANUAL_REVIEW.
- Đã ghi vào: Tiktok-video PROJECT_RULES.md + HANDOFF.md (commit 498fd1f), automation-core
  docs/ui-compatibility-contract.md (commit d850c5a), workspace AGENTS.md.

## 4. Recovery entrypoint — KHÔNG cần config-machine-N.yaml
- Launcher batch dùng chung `D:\CodexRuntime\tiktok-video\config-machine-62.yaml` + `--machine N`;
  workflow tự bound serial/máy từ workbook row ("effective config rebound to this row").
- Sai lầm đã gặp: recovery direct đòi config-machine-18.yaml/32/43/61 → tưởng "device chưa config"
  (BLOCKED_CONFIG_MISSING) — sai, chỉ là chưa dùng đúng entrypoint. Luôn dùng template 62 + --machine N.

## 5. Avatar picker — Recent grid là VIDEO grid (máy 38)
- Symptom: `AVATAR_PICKER_NO_MATCH best=0.466 < 0.600`; log "Download không hiện; giữ Recent grid",
  "using recent Video grid". Ảnh avatar ĐÃ push thành công vào /sdcard/Download/avatar_<folder>.jpg
  (verify: adb shell ls -la /sdcard/Download/ | grep avatar, so sánh size với source).
- Root cause: picker mở tab "Gần đây" = video grid; tile video không bao giờ khớp ảnh avatar.
- Fix hướng (TDD deleg_9dd65023): mở album ảnh thật khi Download/Downloads/Tải xuống vắng
  (thử Hình ảnh/Images/Ảnh/Camera); fallback Recent chỉ khi không có album nào, ưu tiên tile IMAGE
  (bounds/aspect) + MediaStore newest; coordinate fallback chỉ khi evidence ảnh tĩnh, KHÔNG tap mù
  trên video grid. Giữ threshold 0.600 / MAX_TILE_ATTEMPTS 4 / FINAL_BLOCKED khi không khớp.
- PITFALL: "avatar đã push" ≠ "picker thấy ảnh" — verify file trên máy trước, nhưng lỗi thường nằm
  ở việc mở đúng album, không phải thiếu file.