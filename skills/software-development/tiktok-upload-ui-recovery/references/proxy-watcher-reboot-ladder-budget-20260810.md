# B3 soft-reboot với watcher gan-proxy + core kwarg (2026-08-10)

Session evidence: recovery v2/v3 trên máy 5/35/70 (Tik1), commit 9301585 → 43e1825.

## RULE 3 bước fix lỗi UI — budget chốt (user 2026-08-10)

- B1 ATX-kill → B2 force-stop + relaunch (**tối đa 1 lần**) → B3 reboot máy (**tối đa 1 lần**).
- **Budget theo máy trong turn chạy**: 1 relaunch + 1 reboot / máy / turn. Mọi lần lỗi UI lặp lại sau đó **chỉ được ATX-kill + coordinate fallback có evidence** → fail thì MANUAL_REVIEW.
- Lỗi CÙNG CHỖ sau đủ budget = thất bại thật. Lỗi KHÁC CHỖ (state/signature khác) được chạy lại chuỗi, nhưng vẫn nằm trong budget tổng 1 relaunch + 1 reboot của máy.
- Handler đặc thù fail vì UI/dump → route vào ladder, KHÔNG dừng sớm MANUAL_REVIEW.
- Đã ghi vào: PROJECT_RULES.md, HANDOFF.md, AGENTS.md (workspace), automation-core docs/ui-compatibility-contract.md.

## DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED — KHÔNG được chặn B3 khi watcher chạy

- Triệu chứng: ladder chạy đủ tới B3 rồi log `[REBOOT] Guarded reboot recovery failed` / `OWNER_PAUSE_FAILED`, máy không bao giờ reboot.
- Nguyên nhân cũ: `_reserve_proxy_recovery_handoff` trả `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` khi lease thiếu `request_maintenance_handoff` → fail-closed.
- Quyết định user: "Lỗi tiktok thì reboot xong watcher gán vpn làm tiếp" — gan-proxy watcher (`gan_proxy_fleet.py watch --all --workers 80`, poll 30s) chạy ngầm và TỰ gán VPN + publish readiness sau boot. Handoff thủ công thành thừa.
- Fix (9301585): `DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED` → tiếp tục soft reboot với `proxy_handoff=None`, checkpoint reason `proxy_handoff_skipped_watcher_managed`. Các lỗi handoff khác (ACK_INVALID, PRE_REBOOT_BOOT_ID_UNAVAILABLE...) vẫn fail-closed.
- Sau reboot với `proxy_handoff=None` mà máy còn readiness marker → vẫn chờ watcher publish readiness (timeout 60–90s) rồi `require_android_vpn` — không bỏ qua bước chờ.

## BUG CRITICAL: sai tên kwarg core — reboot im lặng không chạy

- Fix 9301585 gọi `reboot_and_restore(wait_for_proxy_ready_before_post_reboot=...)` — tên tự bịa.
- Core thật: `wait_for_proxy_ready_after_reboot=...` (verify bằng `inspect.signature(reboot_and_restore)`).
- Hậu quả: `TypeError: got an unexpected keyword argument` → log `[REBOOT] Guarded reboot recovery failed` → **reboot chưa bao giờ được gọi** dù ladder log nói "soft-reboot đã thử". Mất 2 vòng recovery vì tin log wording.
- Bài học: khi gọi hàm core có tên kwarg dài, **luôn verify signature thật trước** (inspect.signature), không đoán theo log cũ. Log "Ladder cạn (relaunch x2 + soft-reboot đã thử)" chỉ nghĩa là ladder TRY, không nghĩa là reboot THÀNH CÔNG — đọc log-marker `[REBOOT]` riêng.
- Fix (43e1825) + regression test `test_soft_reboot_calls_core_with_correct_proxy_kwarg` (đọc source assert tên kwarg đúng).

## Splash-stuck (kẹt splash đen)

- Visual gate `white=0.000 dark=1.000` = màn đen splash (logo TikTok trên nền đen) — chụp ảnh evidence xác nhận, đừng tin báo "đang ở feed".
- Step (6ad3cfd): wait feed hết timeout mà còn splash → **close recent apps → relaunch TikTok** (không tính ladder B2), budget `SPLASH_STUCK_RECOVERY_MAX=2`, checkpoint `splash_stuck_recovery_used`.
- Máy 5/35/70 kẹt splash đen ngay cả sau relaunch x2 — không phải thiếu wait, là splash-stuck thật; B3 reboot là cứu cánh cuối.

## Recovery entrypoint chuẩn (không tạo config-machine-N)

- Template `D:\CodexRuntime\tiktok-video\config-machine-62.yaml` + `--machine N` bind đúng workbook row ("effective config rebound to this row").
- Lệnh: `echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m tiktok_workflow --config "D:\CodexRuntime\tiktok-video\config-machine-62.yaml" --machine N --no-dry-run --recovery-mode --allow-device-reboot-recovery`
- Mỗi máy 1 process nền riêng; archive lock stale (machine+serial, PID dead proof, backup timestamped) trước khi chạy; giữ foreign locks (tiktok-luot nuoi acc, Tiktok_Reg).

## Regression lesson (caption-field, sáng 2026-08-10)

- Bản mới fail toàn bộ nhóm thử vì siết exact caption-field ID + XML reverify, bỏ generic `edit_text` fallback — trong khi f4e4520 có 32 máy SUCCESS. Đã ghi COMPAT-CAPTION-004: giữ semantic IDs → generic `edit_text` → legacy clipboard flow; XML thiếu/137 không tự thành blocker; không đưa exact-identity fail-closed vào live flow khi chưa có canary nhiều máy.
