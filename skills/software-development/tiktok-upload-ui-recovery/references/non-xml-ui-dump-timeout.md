# non_xml_ui_dump — timeout dump UI quá ngắn (2026-08-10)

## Root cause phát hiện mới

`non_xml_ui_dump` (uiautomator trả XML rác/treo) trên máy farm chậm thường do **timeout dump UI quá ngắn** — không phải lỗi UI build mới.

- Code cũ: `dump_current_ui(timeout=15s)`, `capture_ui_xml(timeout=10-15s)`, `prepare_android_for_automation(timeout=15s)`.
- Máy Samsung G930F cũ dump > 15s → trả XML cụt/không parse → handler tưởng "UI lỗi" → fail sớm MANUAL_REVIEW.
- Triệu chứng đi kèm: `adb uiautomator dump` bị `Killed`, hoặc fail ngay `CONNECT_DEVICE/close_all_apps_start` với `ui_dump_error: non_xml_ui_dump`.

## Fix (commit 7b3bed4, 2026-08-10) — tăng lên 60s ĐỒNG BỘ 5 chỗ

1. `dump_current_ui` def: `timeout=15` → `timeout=60`
2. `StateMachine._handle_connect_device` call: `timeout=10` → `timeout=60`
3. `TikTokAdapter.dump_ui` call `capture_ui_xml`: `timeout=15` → `timeout=60`
4. `prepare_android_for_automation` (startup): `timeout=15` → `timeout=60`
5. `prepare_android_for_automation` (reboot startup): `timeout=15` → `timeout=60`

Test đính kèm cập nhật: `{"timeout": 15}` → `{"timeout": 60}` trong `TestAdapter::test_dump_ui_real_uses_required_shared_capture_contract` + `TestStateMachine::test_shared_android_startup_is_called_once` (2 chỗ, có thể còn chỗ khác nếu grep thấy).

## Pitfall khi làm việc với test file này

- File test TẤT CẢ method nằm TRONG class (`TestStateMachine`, `TestAdapter`...) — **KHÔNG dedent `def test_*` về module-level** vì tưởng là test độc lập. Đã từng phá 28 method, phải `git checkout -- tests/test_tiktok_workflow.py` khôi phục.
- EOL CRLF — sửa bằng python byte-safe (replace CRLF→LF, sửa, restore CRLF), cấm sed/patch trực tiếp file CRLF.

## Quy trình xử lý non_xml_ui_dump còn lại

1. Đã fix timeout → retry máy bằng code mới (60s) trước khi vào ladder.
2. Vẫn fail → RULE 3 BƯỚC: B1 ATX-kill (hồi phục uiautomator) → B2 relaunch 1 → B3 reboot 1, budget máy/turn.
3. Lỗi lặp lại cùng chỗ sau đủ budget → MANUAL_REVIEW.

## Trigger

- `non_xml_ui_dump`, `ui_dump_error`, `DEVICE_STARTUP_FAILED`, `AVATAR_UPLOAD_MENU_MISSING` do dump chết (không đọc được XML picker → không thấy nhãn "Tải ảnh lên").