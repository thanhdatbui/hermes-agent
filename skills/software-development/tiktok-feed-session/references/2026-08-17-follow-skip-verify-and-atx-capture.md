# Follow hook bỏ verify + row trống skip + đọc UI ATX (17/08)

## 1. Follow hook — VERIFY_IDENTITY fail sai chẩn đoán (user chốt: follow liền, bỏ verify)

**User rule 17/08:** "follow hook vào follow liền luôn đéo cần verify củ cặc gì cả vì lúc chọn acc lướt đã chọn acc chuẩn r" — feed preflight (`profile_preflight`) ĐÃ chọn đúng nick row, nên follow hook chạy sau feed KHÔNG cần mở switcher + verify nữa.

**Triệu chứng:** feed SUCCESS nhưng `follow_result.json` báo `CONFIG_ERROR: VERIFY_IDENTITY fail — nick không khớp @<nick> (hoặc switcher fail)`, chạy 4-5 phút rồi fail. KHÔNG phải nick sai — là follow re-verify tốn thời gian + dễ fail máy yếu.

**Fix đã commit (17/08, verify máy 5 OK follow 2 nick lamnhu3003/vantieu11):**
- `tiktok-follow`:
  - `follow_runner/core/config.py`: `FollowConfig.skip_identity_verify: bool = False` (default False — an toàn, chạy tay vẫn verify)
  - `follow_runner/run_follow.py`: `--skip-identity-verify` CLI flag + `cfg.skip_identity_verify = True`
  - `follow_runner/flows/follow_engine.py` `run_session`: khi skip → bỏ `switch_account_and_verify`, set `active_account_handle = row.tik_id` thẳng → follow liền
  - test: `test_skip_identity_verify_skips_switch_and_goes_straight_to_follow` (switcher không được gọi)
- `tiktok-luot nuoi acc`: `_run_follow_hook` (multi_machine_feed_session.py) truyền `--skip-identity-verify` vào command
- Nếu user muốn bỏ verify HẲN mọi trường hợp → đổi default `skip_identity_verify = True` (còn chờ user quyết A/B).

**Cách verify fix:** `python -m follow_runner.run_follow --machine N --config ... --account-row-index R --skip-identity-verify` → `FOLLOW_RESULT {"status": "OK", "followed": [...]}` = qua.

## 2. Row trống (username rỗng) → bỏ qua máy (user rule 17/08)

- `feed_session_workbook.py` `select_feed_session_accounts`: khi row chọn có `expected_username` rỗng → config error `"account row N is empty (no username) for machine M, skipping"` → máy KHÔNG chạy live, ghi `config-error` trong summary, swipes=0.
- TRƯỚC đây behavior là "empty username → dùng current-device account" — đã ĐỔI theo user (row trống thì bỏ qua máy).
- Test cập nhật: 4 test cũ kỳ vọng current-device fallback → đổi thành `config-error` (test_execute_skips_machine_when_username_is_empty, test_missing_serial_still_blocks_current_account_fallback, test_workbook_account_config_errors_are_machine_scoped_and_skip_live_actions, test_workbook_loader_rejects_missing_selected_row_but_allows_empty_username).
- **Pitfall code**: khi MỌI máy config-error (0 máy launch được) → `launch_evidence` chưa khởi tạo → `UnboundLocalError`. Fix: khởi tạo `launch_evidence: dict | None = None` TRƯỚC `if accounts:` trong `execute_multi_machine_feed_session`.

## 3. Đọc UI — ATX primary, tuyệt đối không tin dumpsys một mình

- **`dumpsys window mCurrentFocus` báo SplashActivity là KHÔNG đáng tin** — TikTok giữ splash activity window trong khi feed ĐÃ render. Ảnh thật mới là ground truth (máy 19: dumpsys báo SplashActivity nhưng ảnh rõ ràng For You feed phát video).
- `uiautomator dump` fail `could not get idle state` trên máy yếu khi app đang phát video animation (máy 19 — đúng cảnh báo plan 17/08 upgrade-atx-primary-all-repos).
- ATX session fail với `ATX_SESSION_STUB_NOT_RUNNING` dù `atx-agent` process chạy (PID tồn tại, LISTEN 7912) — stub UiAutomationService không khởi động được.
- **Kết luận máy 19 follow OPEN_TIKTOK_FAILED**: TikTok THỰC SỰ vào feed nhưng mọi backend đọc UI (atx session + shell uiautomator) đều fail vì màn hình không idle → follow báo "TikTok không load feed" SAI. Cần nhìn ảnh trước khi kết luận.
- Patch ATX-primary vào `python_runner/core/ui_capture.py` `capture_required_ui_result`: thêm block đầu gọi `capture_atx_session_ui(adb, timeout, restart_attempts=1)` → XML OK thì trả `CaptureResult(xml, backend=CaptureBackend.ATX_SESSION, capture_id="atx-session-primary", attempts=tuple, artifact_path, diagnostics={"primary": "atx_session"})`; fail → rơi xuống `capture_ui_xml(lightweight=True)` fallback cũ. Chú ý CaptureResult cần đủ 6 field (xml/backend/capture_id/attempts/artifact_path/diagnostics) — thiếu là lỗi constructor.
- `clear-tiktok-cache.py dump_ui` ĐÃ ATX-primary chuẩn (capture_ui_xml trước, shell fallback sau) — không cần sửa.
- Plan: `D:\Taadaa\.hermes\plans\2026-08-17_upgrade-atx-primary-all-repos.md` — `tiktok-luot nuoi acc` là repo mục 7, phần lớn đã đúng, chỉ thiếu ATX-primary block trong ui_capture.py.

## 4. Máy 5 — chuỗi lỗi đã gặp và fix (reference chi tiết)

Feed máy 5 (row 5, thachkieu05, serial 9885e64b4a434a3037) trải qua:
1. **15:45 batch row 5**: tap đúng thachkieu05 (tap_expected_account success) nhưng sau tap → `focused_package: com.android.systemui` → "TikTok focus lost". Nguyên nhân: sau tap nick, Vi Changer VPN reconnect bắn notification → notification shade mở → TikTok mất foreground. Fix `_dismiss_notification_shade_if_open` trong `_navigate_profile_for_preflight` — dismiss shade nếu focus = systemui (swipe up/back + retry 2 lần, try/except an toàn cho test mock).
2. **17:47**: popup "Thêm số điện thoại" (bottom sheet) + keyboard xiaowei → keyboard cleanup fail. Root cause: `_close_candidate` core chỉ nhận close X top<=350, nhưng bottom sheet close X nằm y>350 → add-phone KHÔNG detect → classifier ra for-you. Fix `_bottom_sheet_close_candidate` trong `python_runner/core/benign_popup.py` — accept close label (Đóng/Close/×/X) bất kể vị trí khi đủ 4 markers (title/prefix/input/continue).
3. **PYTHONPATH leak**: chạy background không có PYTHONPATH="" → PIL hermes venv `cannot import name '_imaging'`. Fix: luôn `PYTHONPATH=""` khi chạy feed/follow.
4. **Follow VERIFY_IDENTITY fail** → bỏ verify (mục 1) → follow OK 2 nick.

## 5. Cron row-slot context (nối với tiktok-farm-hermes-cron-migration)

- Manifest 17/08: 247 entries, 74 máy; máy 22 row 1,2,4 (row 3 trống skip); row_slots {1:06:00, 2:08:00, 3:10:00, 4:12:30, 5:15:00, 6:17:30}.
- `run-feed-session.ps1` chạy theo `-Row R -Machines N` — mỗi ticket row 5 ~6 máy due.