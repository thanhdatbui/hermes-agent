# Session reference: TikTok consumer review findings

Các lỗi chỉ lộ ra khi chạy preflight/live trên dữ liệu thật:

## Workbook/Data
- Tik1 dùng header `ID`, không phải `ID TikTok`; canonical alias phải map `ID` → `ID TikTok`.
- OpenPyXL trả `Folder Video` dạng số `489` hoặc float `489.0`; resolver phải canonicalize thành folder `489` ở mọi caller, không ép `str()` ở preflight caller.
- `EmptyCell` trong read-only workbook không đảm bảo có `column_letter`; đọc theo index/header map.
- Machine-first-row có serial rỗng/whitespace phải fail closed.
- Device ID/machine mismatch giữa --machine và --single-device phải reject rõ.

## State machine
- `AccountSource` phải nhận `dry_run` từ state machine; nếu mặc định True thì real workbook update giả thành công nhưng không ghi.
- Video-number override phải cập nhật `context.video_number` để UPDATE_WORKBOOK ghi đúng video thực tế, không ghi posted+1.
- Error reporting path phải dùng `machine.current_state`, không dùng `context.current_state`.
- locked_or_secure guard depends on user environment; farm swipe-only unlock may bypass after core prepare_device wake+swipe+rotation. Do not add PIN/password bypass.
- **`dumpsys window policy` unlock false-positive**: pattern `keyguard(?:Showing|Locked)?\s*=\s*true` matches `deviceHasKeyguard=true` (capability field). Consumer `_is_locked_in_dumpsys` must only match `mShowingLockscreen=true` / `isStatusBarKeyguard=true`.

## Live flow
- TikTok launch: consumer needs force-stop → monkey/am start → `_wait_for_feed` (poll UI for feed indicators like "for you", "following", "đề xuất", "home_tab"; 2s interval, 30s×3 retry). Timeout → MANUAL_REVIEW.
- After soft reboot: must wake screen + swipe unlock before force-stop+relaunch TikTok. Steps: reboot → wait-for-device (120s) → poll boot_completed (60s) → wake (KEYCODE_WAKEUP=224) → swipe unlock (95%→25% height, 500ms, 3 retries, verify via dumpsys) → force-stop → launch → wait_for_feed.
- ACCOUNT_SWITCHER: core `open_profile_root` may fail PROFILE_ROOT_NOT_CONFIRMED on certain TikTok UI layouts. Consumer can add `_fallback_tap_profile_tab` + `_clear_profile_subpage_before_navigation` (back up to 5×) before retry.
- PROFILE_SUBPAGE_STUCK: core `leave_profile_subpage(max_back=1)` insufficient for some TikTok subpages; consumer can pre-clear with back up to 5× before `open_profile_root`.
- TikTok package resolve-activity trả rỗng possible → app corrupted/needs reinstall. `pm resolve-activity com.ss.android.ugc.trill` returns empty → broken install.

## Post-live verification
- Sau live failure cần xác minh workbook không đổi, remote media không có, report MANUAL_REVIEW/FAILED và machine/serial lock release.
- Stale lock PID chết mới được xoá.

## Worker coordination
- Dispatch multiple Codex workers can cause conflicts: one worker reverts another's changes. Use `write_file` (direct rewrite) instead of `patch` when file keeps getting reverted. Or kill active workers before dispatching new one.
- After Codex returns, always dispatch Claude to review actual code before telling user anything. Do not ask user mid-loop.

## TikTok UI selector bugs (session 2026-07-27)
- **`find_by_fields` exact-match trap**: `resource_id=""` chỉ match element có resource-id rỗng. TikTok element thường có `resource-id="com.ss.android.ugc.trill:id/..."` → dùng `resource_id=None` để bỏ qua filter này. Tương tự, `content_desc` exact match không khớp với content-desc động như `"Follow <username>"` → dùng prefix match `desc.startswith("Follow ")`.
- **`already_following` false positive**: `find_by_fields(text="Đã follow")` match nhầm tab navigation "Đã follow" thay vì nút follow của user. Phải thêm `element.clickable` để phân biệt.
- **Follow rate logic trap**: Tab Following/Friends toàn người đã follow → không ai để follow nữa. Đặt follow rate > 0% cho các tab này là vô nghĩa; phải = 0%. Chỉ For You mới có người lạ để follow.
