# Upload batch: ATX/UiAutomator recovery scope, hashtag overlay, stale locks (2026-08-07)

Session: chạy đăng video all máy (Tik1.xlsx qua `run_tiktok_upload_batch.ps1`), fix lỗi UI bằng ATX kill.
Kết quả batch mẫu: 37 verified / 6 SKIPPED_LOCKED / 37 lỗi (phân loại bên dưới).

## Stale device locks — phải dọn CẢ `machine_X` + `serial_<serial>`

- Mỗi máy có thể có **2 lock file**: `machine_<n>.lock.json` VÀ `serial_<serial>.lock.json`
  (`device_lock_paths` sinh cả 2; `machine_inventory._filter_locks` check cả 2).
- Pitfall thật: chỉ archive `machine_*.lock.json` xong, preflight vẫn báo 74 `SKIPPED_LOCKED`
  vì 74 file `serial_*.lock.json` còn nguyên.
- Kiểm tra PID sống bằng **wmic** (tasklist silent-fail trên git-bash):
  `wmic process where "ProcessId=N" get ProcessId` — có dòng == N là ALIVE.
- Archive pattern (move, không xóa): `D:\CodexRuntime\tiktok-video\stale-lock-archive\<ts>_m<machine>`
  (precedent có sẵn `20260730_*`). Giữ: lock PID còn sống + máy user chỉ định giữ.
- Preflight read-only trước live:
  `PYTHONPATH=D:/Taadaa/Tiktok-video/scripts <venv>/python.exe -m tiktok_workflow.machine_inventory --workbook D:/OneDrive/Tiktok/Tik1.xlsx`
  → đọc `eligible` / `skipped`. Script tiện: `scripts/check-stale-locks.py`.

## ATX kill (`_recover_uiautomator`) — khi nào đủ, khi nào cần reboot

Core `ui.py::_recover_uiautomator` tự chạy trong `capture_ui_xml`: force-stop
`com.github.uiautomator*`, pkill `atx-agent`, pkill `uiautomator`, `uiautomator quit`.
Consumer Tiktok-video gọi qua `adapter._dump_ui_real` → `capture_ui_xml(..., recovery_package="com.ss.android.ugc.trill")`.

Phân biệt 2 signature:

| Signature | Chẩn đoán | ATX kill đủ? |
|---|---|---|
| dump exit **137 (Killed)** | `ps -A \| grep -iE 'atx\|uiauto'` có process `com.github.uiautomator` | ✅ pkill giải phóng accessibility handle → dump OK ngay |
| **"could not get idle state"** dai dẳng | KHÔNG có process uiautomator, `enabled_accessibility_services=null` | ❌ service chết hẳn → cần reboot (consumer có soft-reboot recovery, `SOFT_REBOOT_RECOVERABLE_STATES` gồm DISMISS_POPUPS/OPEN_TIKTOK/... nhưng không trigger cho signature này) |

Verify tay: `uiautomator dump /sdcard/wd.xml`; nếu 137 →
`pkill -f atx-agent; pkill -f uiautomator` → dump lại OK (đã chứng minh trên máy 1).
Sau khi hồi phục dump, **UI dump OK ≠ màn hình OK** — luôn screenshot/vision để xác nhận surface thật.

## POST_CONTROL_OCCLUDED — overlay hashtag che nút Đăng

- Composer TikTok: mở hashtag suggestion overlay → che nút "Đăng" (Post) top-right
  → worker không recapture được composer có guard caption + Post → MANUAL_REVIEW.
- Overlay **KHÔNG có nút X**. Back (`input keyevent 4` hoặc tap mũi tên top-left
  bounds [18,72][150,204]) **thoát hẳn composer** — không đóng overlay.
- Fix đúng: **tap vào caption field** (bounds ~[48,229][615,694]) → overlay đóng →
  nút "Đăng" (resource-id `smf`, bounds [794,90][1032,186]) hiện lại → tap Đăng.
- Worker fail vì chỉ thử 1 Back → recapture không ra composer.

## Battery saver dialog (PIN YẾU) occlude UI

- S7 pin ≤ ~15%: dialog "PIN YẾU" (battery saver) tự bật, che UI giữa chừng → gây
  POST_CONTROL_OCCLUDED / recapture fail lặp lại.
- Đây là lỗi MÔI TRƯỜNG, không phải UI handler — đóng dialog (`input keyevent 4`) rồi retry;
  pin vẫn yếu → sạc máy trước, đừng cố đăng (dialog sẽ bật lại).

## Batch launcher — background qua pipe không exit

- `run_tiktok_upload_batch.ps1 ... 2>&1 | tail -60` (background) **KHÔNG BAO GIỜ exit**:
  pipe giữ EOF → `notify_on_complete` không fire → phải kill thủ công.
- Đúng: redirect thẳng ra file `> log 2>&1`, không pipe qua tail.
- Launcher hard-check automation-core version (0.4.40). Hermes terminal PYTHONPATH trỏ
  hermes-agent venv → import nhầm automation-core 0.4.32 → version mismatch.
  Fix: chạy với `PYTHONPATH=` rỗng (đã có trong memory).

## Gom report lỗi sau batch

- `runs/run_*/report.json` chứa `status` / `reason` / `post_verified` / `post_submission_state`.
- Map serial→máy từ workbook, lọc report theo timestamp khung giờ batch, group theo reason.
- `post_submission_state: None` = worker CHƯA tap Đăng → composer còn nguyên → retry tay an toàn
  (không sợ đăng 2 lần). `post_verified: false` + status SUCCESS = bài ĐÃ đăng (ACCEPTED) → hậu kiểm.
- Lỗi batch mẫu 2026-08-07: UI_DUMP_FAILED 11 máy, OPEN_TIKTOK_FAILED 9, DEVICE_STARTUP_FAILED 5,
  POST_RECHECK_UNAVAILABLE 2, POST_CONTROL_OCCLUDED 1, MEDIA_FINGERPRINT_PENDING 1, VIDEO_PICK_SHOP_REPLAY_CARD 1,
  MISSING_ID 6 (73,75,77,78,79,80 — workbook thiếu ID TikTok → fail-closed ngay).
