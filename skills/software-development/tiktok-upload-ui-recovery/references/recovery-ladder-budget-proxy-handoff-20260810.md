# Recovery ladder budget chốt 2026-08-10 + proxy handoff B3 + entrypoint recovery

Bối cảnh: batch Tik1 20260810 — bản cũ f4e4520 32 SUCCESS; m5/m35 kẹt splash đen; m27
shop-replay-card UI dump fail; m70 DISMISS_POPUPS UI dump fail. Sau nhiều vòng recovery,
user chốt rule 3 bước (ghi PROJECT_RULES.md / HANDOFF.md / AGENTS.md workspace /
automation-core docs/ui-compatibility-contract.md).

## Rule 3 bước — budget chốt (user 2026-08-10)

- B1: ATX-kill (uiautomator recovery)
- B2: force-stop + relaunch app — TỐI ĐA 1 lần
- B3: reboot máy (soft reboot) — TỐI ĐA 1 lần
- **Budget theo máy trong turn chạy của nó**: 1 relaunch + 1 reboot/máy/toàn bộ turn.
  Mọi lần lỗi UI lặp lại SAU đó chỉ được ATX-kill + coordinate fallback có evidence
  (KHÔNG relaunch/reboot nữa) → fail thì MANUAL_REVIEW.
- Lỗi CÙNG CHỖ sau đủ budget = thất bại. Lỗi KHÁC CHỖ (state/signature khác) được
  chạy lại chuỗi 3 bước nhưng VẪN nằm trong budget tổng 1 relaunch + 1 reboot của máy.
- Handler đặc thù fail vì UI/dump → phải route vào ladder, KHÔNG dừng sớm MANUAL_REVIEW.
- Lý do budget: relaunch/reboot chỉ cứu trạng thái máy xấu; đã reboot 1 lần mà vẫn lỗi
  → vấn đề là logic/verifier/UI build, reboot thêm chỉ tốn thời gian.

## DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED — KHÔNG chặn B3 reboot (fix 9301585)

- Hiện tượng cũ: `_maybe_soft_reboot_recovery` gọi `_reserve_proxy_recovery_handoff`;
  nếu lease không hỗ trợ `request_maintenance_handoff` (device_lease không có method)
  → trả `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` → workflow coi RECOVERY_FAILED,
  KHÔNG reboot → ladder B3 chết, máy kẹt splash đen mãi (m5/m35/m70 v2).
- Fix (commit 9301585): khi lỗi handoff = `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` và
  gan-proxy watcher đang chạy ngầm (`gan_proxy_fleet.py watch --all --workers 80`,
  poll 30s, runtime D:\CodexRuntime\codex_gmail_debug-gan-proxy) → KHÔNG fail-closed:
  tiếp tục reboot với proxy_handoff=None, checkpoint reason `proxy_handoff_skipped_watcher_managed`.
  Các lỗi handoff khác (ADB_CLIENT_UNAVAILABLE / PRE_REBOOT_BOOT_ID_UNAVAILABLE /
  ACK_INVALID / ACK_INCOMPLETE) vẫn fail-closed.
- Sau reboot khi proxy_handoff=None nhưng readiness_marker tồn tại → vẫn phải chờ
  watcher publish readiness: `wait_for_proxy_ready(serial, post_boot_id, timeout=60-90s)`
  rồi `require_android_vpn` — watcher tự gán VPN lại sau boot (user: "Lỗi tiktok thì
  reboot xong watcher gán vpn làm tiếp; mắc gì lỗi").
- Nguyên tắc vận hành: watcher gan-proxy là self-managed — workflow KHÔNG cần handoff
  thủ công quanh reboot; chỉ cần chờ readiness sau boot.

## Entrypoint recovery — KHÔNG đòi config-machine-N.yaml (sai lầm 2026-08-10)

- Sai lầm: recovery báo `BLOCKED_CONFIG_MISSING` vì không có `config-machine-18.yaml`
  v.v. → user: "ủa chạy fix recovery k đc các máy lỗi luôn à? cần tao hướng dẫn từng máy k".
- Đúng: batch/recovery dùng template `D:\CodexRuntime\tiktok-video\config-machine-62.yaml`
  + `--machine N`; workflow bind serial từ workbook row
  (log: `Target binding: workbook row machine=N serial=...; effective config rebound to this row`).
- Lệnh chuẩn từng máy (1 process nền độc lập, không loop shell):
  `echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow --config "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" --machine N --no-dry-run --recovery-mode --allow-device-reboot-recovery > /d/CodexRuntime/tiktok-video/recovery-<tag>-mN-<ts>.log 2>&1; echo WORKER_EXIT=$?`

## Batch KHÔNG tự recovery sau lỗi

- Batch chỉ chạy 1 lượt; máy lỗi → giữ handoff lock (owner_active=false, PID dead),
  ghi report, chuyển máy tiếp. Muốn retry phải dispatch recovery riêng (release stale
  lock archive + chạy lại từng máy).
- Lock cũ release điều kiện: project=tiktok-upload, status=handoff, owner_active=false,
  PID dead (WMIC /format:list), không replacement worker; archive cả 2 alias
  (machine_N + serial_hex) + evidence JSON; KHÔNG đụng foreign lock
  (tiktok-luot nuoi acc / Tiktok_Reg).

## Splash-stuck recovery (code 6ad3cfd)

- `_recover_splash_stuck()`: khi WAIT_FEED hết timeout mà TikTok foreground không feed
  (splash đen: visual gate `white=0.000 dark=1.000`) → đóng Recent apps
  (`close_all_recent_apps`) → launch lại TikTok → quay lại wait feed.
  Budget `SPLASH_STUCK_RECOVERY_MAX=2`, checkpoint `splash_stuck_recovery_used`;
  KHÔNG dùng prepare_app_for_automation nên không nhầm ladder B2.
- Ảnh evidence `coordinate-fallback-open_tiktok-before.png` toàn đen = splash hoặc màn
  tắt thật — check màn thật TRƯỚC khi kết luận (đừng chỉ đọc pixel).
- Log-marker ladder mới: `[OPEN_TIKTOK] Ladder cạn (relaunch x2 + soft-reboot đã thử)`,
  `Coordinate fallback evidence screenshot: ...`, `FINAL_BLOCKED (không tap mù)`,
  `UI_FAILURE_LADDER_B2`, `Classified recovery stopped before generic retry` (cũ, đã bỏ).

## Regression caption-field — cấm tái diễn (COMPAT-CAPTION-004, commit 5faf905)

- Bản mới sau f4e4520 fail toàn bộ nhóm thử vì siết exact caption-field ID + XML
  reverify fail-closed; bản cũ có generic `edit_text` fallback + clipboard flow → 32 SUCCESS.
- Giữ thứ tự: semantic IDs → generic `edit_text` fallback → legacy clipboard flow.
- XML thiếu/malformed/137 không tự động thành blocker nếu fallback vẫn hoạt động.
- Không đưa fail-closed exact identity vào live flow khi chưa có canary multi-machine.
