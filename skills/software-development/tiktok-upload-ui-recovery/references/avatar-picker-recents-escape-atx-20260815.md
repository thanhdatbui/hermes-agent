# Avatar picker + Recent-apps escape + ATX zombie — 2026-08-15 farm session

Kết quả live farm Tik2 (56 máy avatar-only, 54/56 success). Mọi fix đều được
encode vào canonical `D:\Taadaa\Tiktok-video` và commit `e329cc7`.

## Rule 3 bước — user xác nhận lại chính xác (quan trọng)

- **B1 ATX-kill: LIÊN TỤC** — gọi ở MỌI lần gặp lỗi UI, không giới hạn:
  - giữa các attempt trong `_execute_with_ui_retry` (state_machine.py) —
    phải gọi `_recover_uiautomator(adb, timeout=10, attempts=[], label="ui_retry_atx_kill")`
    TRƯỚC mỗi retry attempt (`if attempt < self.ui_retry_limit and not is_ui_unavailable`)
  - trong `_run_ui_failure_ladder` (B1), WAIT_FEED, CONNECT_DEVICE
- **B2 relaunch: bounded ×1** (`APP_RELAUNCH_MAX_ATTEMPTS`)
- **B3 soft reboot: bounded ×1/signature** — `attempts[signature] >= 1 → return False`
  (state_machine.py `_maybe_soft_reboot_recovery`) + tổng `soft_reboot_recovery_max_total`
- Trước 2026-08-15 CONNECT_DEVICE chỉ chạy B1 rồi `return False` NGAY → bỏ qua
  B2/B3 → `DEVICE_STARTUP_FAILED: non_xml_ui_dump`. Fix: sau B1 thử B2
  (re-run `prepare_android_for_automation`), nếu vẫn fail → set error +
  `_maybe_soft_reboot_recovery()` (B3) rồi mới return False.

## COMPAT-RECENTS-ESCAPE-001 — máy kẹt Recent apps

Triệu chứng: sau B3 soft reboot, nhiều máy kẹt ở màn hình Recent apps (App
Switcher, nút "ĐÓNG TẤT CẢ"). `close_all_recent_apps` cần uiautomator dump để
tìm nút clear-all; uiautomator chết (`non_xml_ui_dump`) → fail → app không
launch → `AVATAR_UPLOAD_MENU_MISSING` (không thấy "Tải ảnh lên").

Fix (encode vào `_handle_open_tiktok`, trước mỗi `prepare_app_for_automation`):
```python
focused_pkg, focused_act = self._read_focused_activity(adapter)
if focused_act and ("recents" in focused_act.lower() or "recent" in focused_act.lower()):
    adapter._adb.shell(["input", "keyevent", "3"], timeout=10, check=False)  # HOME
    time.sleep(1)
```
Bấm HOME (keyevent 3) thoát Recent KHÔNG cần uiautomator dump. Máy 69/71 pass
sau khi thoát Recent tay rồi chạy lại.

Debug path: máy kẹt Recent → `exec-out screencap` thấy App Switcher grid →
tap card app giữa màn hình để vào app → chạy lại workflow. Luôn encode
workaround đã chứng minh vào canonical script (user rule).

## ATX zombie / wedged — máy 27, 32

- Máy 27: atx-agent chạy `server -d --stop` (STUCK STOP-process, do tool mirror
  respawn) → `pkill -9 -f atx-agent` + force-stop sạch mà dump vẫn
  `could not get idle state` → dịch vụ hư vĩnh viễn, chỉ B3 reboot giúp.
- Máy 32: atx-agent `futex_wait_queue_me` (S-state wedged, SIGTERM không ăn)
  → `pkill -9` hồi phục ngay (dump OK) → avatar up thành công.
- Tool mirror (数卫安卓投屏 v9.5.45 VIP, grid 80 màn hình) respawn atx-agent
  `--stop` → kill tay thành treadmill; kill nhiều lần làm hư uiautomator vĩnh
  viễn — prefer cá nhân hóa B3 reboot thay vì kill loop.

## Turn mới = budget mới (retry máy MANUAL_REVIEW)

Máy fail MANUAL_REVIEW sau khi cạn ladder (B1/B2/B3 hết budget trong turn) có
thể CHẠY ĐƯỢC ở turn kế tiếp: uiautomator hồi phục sau thời gian idle (máy 27
fail 16:09-16:23 với `uiautomator_null_root_node` sau reboot, nhưng 16:35
`uiautomator dump` test OK → chạy lại THÀNH CÔNG). Quy tắc:
- Trước khi retry máy MANUAL_REVIEW, dump-test tay: `adb shell 'uiautomator dump
  /sdcard/t.xml'` — nếu ra `UI hierarchy dumped` thì chạy lại workflow ngay.
- Không kết luận "máy hư vĩnh viễn" từ 1 turn thất bại; budget reset theo turn.
- Mỗi lần chạy lại = manifest mới đúng danh sách máy (xem pitfall dưới).

## Pitfall: manifest resources phải khớp chính xác -ForceAvatarMachineList

Chạy launcher với `-ForceAvatarMachineList '27'` nhưng manifest chứa
`resources: ["machine:27", "machine:32"]` → fail ngay:
`Machine inventory preflight failed: INVENTORY_ERROR: assignment preflight
failed: AssignmentError` (trước khi khởi động runner nào).
Fix: tạo manifest mới có resources khớp đúng danh sách máy đang chạy
(ví dụ chỉ `machine:27`), đừng tái dùng manifest cũ của batch lớn hơn.

## COMPAT-AVATAR-011 — picker order

Push + MediaStore index TRƯỚC, mở photo picker SAU. Grid picker chụp snapshot
khi mở — mở trước push → grid stale → tap trượt / không thấy ảnh mới. Máy 4
+ máy 7 canary pass, verify profile thật = ảnh người.

## Verifier avatar-only — run_tiktok_upload_batch.ps1

Verifier chỉ nhận `status=="SUCCESS" AND post_verified==$true` → avatar-only
luôn MANUAL_REVIEW → đếm LỖI sai. Fix:
```powershell
elseif ($AvatarOnly) { [bool]($report -and $report.status -eq "AVATAR_SMOKE_SUCCESS") }
```
Batch 1/2 chạy verifier cũ → kết quả KHÔNG tin được, phải chạy lại. Tổng hợp
cuối đọc report.json từng máy, không tin launcher summary.

## Avatar mass generation

- Regenerate avatar cho 55 máy lỗi + 335 folder còn lại (cả 2 root:
  `D:\video goc` + `D:\TIKTOK-videonuoinick`) bằng 4 worker song song
  (avatar_worker.py, mỗi worker ~69 folder, ~25 phút).
- `_make_avatar.py` hardcode `SOURCE_ROOT=D:\video goc` → folder tv_only
  (298+) phải gọi `make_representative_avatar` trực tiếp (bypass root cứng).
- Ưu tiên avatar: kênh thật → người/động vật (YOLO theo niche) → frame sáng
  crop 512×512 (KHÔNG frame đầu bừa).
- `download_by_niche.py`: thêm `make_avatar_for_folder` fallback — nếu
  `download_channel_avatar` fail thì tạo từ frame theo `subject_type` niche.