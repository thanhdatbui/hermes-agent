# uiautomator Killed EXIT=137 — force-stop atx (nhanh) trước reboot (2026-08-06)

## Bối cảnh

Session đăng video Tik1 (2026-08-06): máy 10 + 30 fail `POST_RECHECK_UNAVAILABLE` /
`UI_DUMP_FAILED` nhiều lần vì uiautomator treo (`Killed`, E=137, `Bad file descriptor` —
UiAutomationService treo). Skill cũ ghi "reboot là fix duy nhất" — SAI.

## Fix 1 (NHANH — live-proven 2026-08-06)

`am force-stop com.github.uiautomator` → dump trả E=0 NGAY, KHÔNG cần reboot.
atx-agent tự restart lại service sạch. Máy 30 chạy qua được và ĐĂNG THÀNH CÔNG nhờ fix này.

```bash
ADB="/c/Program Files (x86)/xiaowei/tools/adb.exe"
adb -s <serial> shell am force-stop com.github.uiautomator
sleep 3
adb -s <serial> shell "uiautomator dump /sdcard/wd.xml 2>&1; echo E=$?"   # mong đợi E=0
```

- `killall com.github.uiautomator` báo "No such process" (package đã force-stop) — bỏ qua, vô hại.
- Trước khi force-stop: atx-agent + `com.github.uiautomator` process VẪN sống (ps -A thấy),
  `accessibility_enabled` có thể `null` hoặc trỏ TalkBack — nhưng dump vẫn Killed → đừng chẩn đoán
  theo process sống, cứ force-stop.
- Verify sau fix: `uiautomator dump` E=0 + `ip addr show tun0 | grep -c inet` = 1 (VPN không mất
  vì không reboot).

## Fix 2 (fallback khi force-stop không ăn)

`adb reboot` mềm → dump E=0. Sau reboot PHẢI gán lại VPN:
`set_proxy` (vi_changer_runner) — watcher không tự gán sau reboot tay.
Trình tự: ghi nhận tun0 trước → reboot → wait-for-device → boot_completed=1 → set_proxy → verify dump.

## Pitfall: treo LẠI giữa run

Máy có thể treo lại NGAY trong run sau đó (VERIFY_POST/POST_RECHECK cần dump).
Máy 10: force-stop ăn lúc đầu (E=0) nhưng treo lại 4 lần liên tiếp, mỗi lần VERIFY_POST fail
`ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account` (dump rỗng lúc verify).
Rule: fix 1 thành công 1 lần ≠ máy hết bệnh. Cùng signature ≥2 lần sau fix → DỪNG theo
Recovery Contract, chuyển MANUAL_REVIEW + hậu kiểm tay, không force-stop-rerun vô hạn.

## Chẩn đoán nhanh

```bash
adb -s <serial> shell "ps -A | grep -E 'atx|uiautomator'"      # process có sống không
adb -s <serial> shell "uiautomator dump /sdcard/wd.xml 2>&1; echo E=$?"   # E=137 = treo, E=0 = OK
adb -s <serial> shell "ip addr show tun0 2>/dev/null | grep -c inet"      # VPN còn không
```

## Pitfall: preflight luôn SKIPPED_LOCKED dù `-RecoveryMode` (2026-08-06)

`machine_inventory.py` `_filter_locks` chỉ kiểm tra lock FILE tồn tại — lock `handoff`
(kể cả PID chết) vẫn bị skip ở preflight; `-RecoveryMode` KHÔNG qua được filter này →
"Máy mục tiêu: none" + 0 runner (dính 2 lần cùng ngày khi retry 11 máy có lock handoff).
`-RecoveryMode` chỉ ảnh hưởng worker lúc chạy live (takeover trong run), KHÔNG ảnh hưởng inventory.

**Cách chuẩn: xoá lock stale TRƯỚC preflight** (cả `machine_<N>.lock.json` VÀ
`serial_<serial>.lock.json`, guard status=handoff + PID chết + backup trước) — không dựa vào
RecoveryMode để qua filter. Sau khi xoá, preflight thấy máy eligible bình thường.

## CAPTION signature mới: "Paste action not found" (máy 74, 2026-08-06)

Máy 74 (TikTok 46.2.3) vào CAPTION_FILL, "Filling caption via clipboard" nhưng sau đó
`[WARNING] Paste action not found` (attempt 1/3) → fail 3 attempts → MANUAL_REVIEW.
KHÁC với CAPTION-001 (clipboard broadcast not-ok) và CAPTION-003 (escape `#`):
lần này broadcast `clipboard.set` KHÔNG fail (`Filling caption via clipboard` không báo lỗi),
nhưng **thao tác dán (paste) không tìm thấy nút/action paste** trong composer.

- Chưa có handler riêng — theo rule bắt buộc: phân loại signature + thêm handler
  (tìm selector nút Paste / fallback gõ tay) + regression test + COMPAT entry TRƯỚC khi retry máy 74.
- Phân biệt với caption fail khác: xem log dòng cụ thể (`Clipboard setup failed` = CAPTION-001/003,
  `Paste action not found` = signature MỚI chưa có handler).
- Máy 74 cùng ngày còn dính `adb command timed out: ... input tap` lúc VIDEO_PICK
  (máy chậm, >10s/tap) — máy này cần retry timeout dài hơn.

## Tổng kết

- Skill cũ: "reboot là fix duy nhất" → SAI, đã sửa: **force-stop package uiautomator trước, reboot fallback**.
- Batch Tik1 2026-08-06: máy 30 hoàn tất nhờ force-stop; máy 10 dừng sau 4 lần (treo lại giữa run).
- Máy 74: CAPTION signature mới `Paste action not found` — cần handler + COMPAT trước khi retry.

## ROOT CAUSE THẬT — atx-agent process giữ handle treo (2026-08-06, máy 10/30)

Force-stop package uiautomator (Fix 1) KHÔNG giải phóng UiAutomationService handle
khi atx-agent process đang giữ nó → máy vẫn treo lại sau run (máy 10 treo 4 lần).

**Fix live-proven**: `adb -s <serial> shell pkill -f atx-agent` → dump E=0 NGAY,
`com.github.uiautomator` process cũng biến mất. Nhanh hơn reboot, không mất VPN.

**Đã đưa vào automation-core 0.4.36** (commit trong repo core):
- `ui.py::_recover_uiautomator` — sau force-stop package, pkill process `atx-agent`
  (scoped marker, không kill broad); log `process_killed` vào recovery entry.
- `ui_xml.py::_ERROR_MARKERS` — thêm `"killed"` + `"bad file descriptor"` để
  classify đúng signature UiAutomationService wedged (trước đây fall `non_xml_ui_dump`).
- Regression test `tests/test_ui_dump.py::test_dump_kills_atx_agent_process_when_service_wedged`
  (mock dump trả "Killed"/137 + ps -A có atx-agent → assert force-stop + pkill, không reboot).
- Test suite: 22/22 (test_ui_dump + test_persistent_ui) + 73/73 (recovery/circuit) pass.
- Wheel `automation_core-0.4.36-py3-none-any.whl` build xong; cài vào
  venv-core024 (launcher pin 0.4.35 → 0.4.36 trong run_tiktok_upload_batch.ps1).
- LƯU Ý khi cài: PYTHONPATH hermes venv nhiễm → pip install phải `env -i` sạch,
  nếu không cài nhầm vào hermes venv (version vẫn 0.4.32).

**Thứ tự recovery nhanh cho mọi consumer gặp uiautomator lỗi**:
1. `am force-stop com.github.uiautomator`
2. `pkill -f atx-agent`
3. `adb reboot` (chỉ khi 1+2 không ăn) + `set_proxy` lại VPN sau reboot

Chẩn đoán treo: `uiautomator dump` trả `Killed`/`E=137` + `ps -A | grep atx-agent` còn sống.
