# state_machine.py fixes 2026-08-10 (Tiktok-video, m5/m34/m36/m38)

## 1. CONNECT_DEVICE B1 ATX-kill (commit 7d01c52, sau 7b3bed4)

**Bug**: máy dính `non_xml_ui_dump` tại `close_all_apps_start` (CONNECT_DEVICE
startup) fail ngay attempt 1 → MANUAL_REVIEW, ladder B1 ATX-kill KHÔNG BAO GIỜ
chạy. Lý do kép:
- `_handle_connect_device` set `is_ui_unavailable=True` + return False → retry
  wrapper break ngay (không attempt 2/3).
- `_run_ui_failure_ladder` lấy `adb = adapter._adb` nhưng `adapter` được tạo
  SAU startup thành công → `adapter=None` → `adb=None` → B1 vô hiệu.

**Fix**: trong `_handle_connect_device`, khi startup fail vì UI/dump → gọi
`_recover_uiautomator(self.context.adb_client, timeout=10, attempts=[],
label="connect_device_atx_kill")` TRƯỚC khi set `is_ui_unavailable`.
`adb_client` có sẵn trong context, không phụ thuộc adapter.

**Cùng phiên**: timeout dump UI 10/15s → 60s (4 chỗ `dump_current_ui`/
`capture_ui_xml` + 2 chỗ `prepare_android_for_automation(timeout=15)` →
60; commit 7b3bed4). Lưu ý: non_xml_ui_dump KHÔNG phải lỗi timeout — là
uiautomator TREO (adb test tay: `uiautomator dump` bị Killed). Fix đúng = B1
ATX-kill; timeout 60s chỉ giúp máy chậm, không cứu uiautomator treo.

**Kết quả live**: m5 sau fix: `close_all_apps_start: success` + WAIT_FEED tự
ATX-kill recovery → SUCCESS post ACCEPTED (run 211228).

## 2. Popup quyền media trước foreground gate (commit e83a786, m34)

**Bug**: `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] TikTok foreground could not be
verified before recovery`. Android 13+ bật popup "Cho phép TikTok truy cập
ảnh, phương tiện và tệp" (READ_MEDIA_IMAGES/VIDEO, KHÔNG grant được qua
`pm grant`) NGAY SAU create tap → `com.google.android.packageinstaller`
(GrantPermissionsActivity) chiếm foreground → `_package_is_foreground(trill)`
= False → fail sớm, không bao giờ tới loop allow permission (dòng ~7973).

**Fix**: trong `_recover_video_pick_create_entry`, TRƯỚC khi finalize
foreground gate → `adapter.dump_ui()` + `_allow_tiktok_permission(adapter,
popup_xml)`; nếu allow → `_record_video_pick_recovery(...pre_gate)`, sleep 1,
re-check foreground (chưa về trill thì `_bring_adapter_to_foreground`); chỉ
khi vẫn không phải trill mới finalize fail.

**UI thật (screenshot m34 21:46)**: popup có nút `CHO PHÉP`/`TỪ CHỐI` +
"Thay đổi cài đặt của bạn". PHẢI bấm CHO PHÉP — từ chối → TikTok không đọc
được media → picker trống → không upload được.

**Test TDD**: `test_video_pick_create_entry_allows_permission_popup_before_foreground_gate`
— fake adapter dump_ui trả popup packageinstaller lần 1, `_package_is_foreground`
sequence [False, True, True] (3 lần gọi), `_allow_tiktok_permission`
monkeypatch tăng `allow_count` → assert recovery True + allow_count ≥ 1.

## 3. AVATAR-ONLY rule (user chốt)

- CHỈ đổi avatar → `--avatar-smoke --force-avatar-upload --force-avatar-machines N`
  (flow RESOLVE → ENSURE_AVATAR → RELEASE; KHÔNG push video/post/workbook).
- CẤM `--force-avatar-upload` đơn lẻ cho avatar-only — nó chạy FULL flow
  (push video + POST) rồi mới tới ENSURE_AVATAR → đăng video thừa (m38 tile
  12→13 vô ý 2026-08-10).
- m36/m38 đổi avatar OK 19:54: `AVATAR_SMOKE_SUCCESS /
  FORCED_REPLACED_VERIFIED` (picker 0.642/0.989; verify sau save 0.985/0.988).

## 4. Avatar picker album ảnh (commit ccd28f3)

- Recent grid ("Gần đây") là VIDEO grid — tile video không bao giờ khớp avatar
  source. Khi "Download"/"Tải xuống" vắng mặt → thử album ảnh:
  `Hình ảnh / Images / Ảnh / Camera`; chỉ khi KHÔNG có album nào mới fallback
  Recent, và lúc đó ưu tiên IMAGE tile (bounds/aspect), không tap tile đầu mù.
- Coordinate fallback chỉ khi evidence ảnh tĩnh (visual match
  `_avatar_picker_visual_match`); không tap mù trên video grid.
- Giữ threshold 0.600 / max 4 attempts / FINAL_BLOCKED khi không match.

## 5. COMMIT GATE (user chốt chính sách, ghi PROJECT_RULES.md mọi repo)

- Commit + push KHI FULL TEST SUITE XANH (pytest tests/ -q, không chờ
  live-run success). Live-run là verify TIẾP (lỗi mới → fix tiếp commit tiếp).
- Fix sai trên máy thật → revert NGAY bản git trước (git revert/checkout).
- Bài học đi kèm: subagent có thể chết giữa chừng (tool-iteration cap / PC
  sleep) để lại code dở compile-OK nhưng chưa commit → verify diff + full
  suite rồi commit thay (session này: agent avatar-picker chết, tao verify 330
  passed + commit thay).

## 6. PC sleep giết worker

PC sleep/khóa màn giết worker giữa chừng → lock còn `handoff` PID dead →
archive lock (backup + evidence) rồi retry. Không coi đó là fail của code.
