# Fixes 2026-08-10 — non_xml_ui_dump + avatar-only + add-phone

## non_xml_ui_dump = uiautomator TREO, không phải timeout

- Triệu chứng: `[DEVICE_STARTUP_FAILED] ui_dump_error: non_xml_ui_dump` tại `CONNECT_DEVICE/close_all_apps_start`, `[AVATAR_UPLOAD_MENU_MISSING]` / `[AVATAR_PICKER_NO_MATCH]` (picker không thấy tile/label vì XML rác).
- Nguyên nhân thật: uiautomator service bị treo (adb `uiautomator dump` bị `Killed`), **không phải timeout ngắn**.
- Đã thử: tăng timeout dump 10/15s → 60s (commit 7b3bed4, 4 chỗ dump + 2 chỗ prepare_android_for_automation). Cứu được máy 34 nhưng KHÔNG cứu máy 5 — chứng tỏ treo không phải timeout.
- Fix đúng: **B1 ATX-kill** (restart uiautomator service) → retry. Nếu workflow dừng sớm ở CONNECT_DEVICE trước ladder → ATX-kill tay trước khi chạy lại.
- Verify: `adb -s <serial> shell uiautomator dump /sdcard/d.xml && cat /sdcard/d.xml` — nếu bị Killed/trống → uiautomator treo.

## AVATAR-ONLY (chỉ đổi avatar)

- Dùng đúng: `--avatar-smoke --force-avatar-upload --force-avatar-machines N` → flow RESOLVE → ENSURE_AVATAR → RELEASE (không push video, không post, không ghi workbook).
- CẤM dùng `--force-avatar-upload` đơn lẻ cho avatar-only — nó chạy FULL flow (push video + POST) rồi mới tới ENSURE_AVATAR → đăng video thừa (m38 tile 12→13, 2026-08-10).

## add-phone KHÔNG sensitive

- Popup add-phone là benign: dismiss tự động (consumer tap close; core 0.4.40 chỉ EN, fix 0.4.44).