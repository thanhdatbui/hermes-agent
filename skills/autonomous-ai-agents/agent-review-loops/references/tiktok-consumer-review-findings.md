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

## AI Auto-Recovery & Popup / Overlay Handling (Session 2026-08-21)
- **CẤM Hardcode Tọa độ trong AI Auto-Recovery Patch:**
  - AI Vision (Gemini 3.7) thường có xu hướng sinh code dùng `ctx.tap(x, y)` theo pixel cứng thay vì bóc tách cây XML. Điều này gây trượt nút hoặc chạm nhầm nút lân cận (ví dụ quẹt trúng nút Camera `[+]` ở đáy màn hình `Y=1800+`).
  - **Quy tắc bắt buộc:** Bắt buộc AI sinh code tìm Element UI qua `parse_xml`, `iter_elements`, `parse_bounds` và tìm đúng text/content-desc (`"Đóng"`, `"Hủy"`, `"X"`, `"Close"`...) để tính tâm `bounds` động `((b[0]+b[2])//2, (b[1]+b[3])//2)`. Chỉ dùng tọa độ tỷ lệ màn hình làm fallback tầng cuối cùng.
- **Fail-Closed khi đối soát Profile (`_verify_profile_after_session`):**
  - Không được quy kết các lỗi như màn hình kẹt Camera / Overlay / mạng lag chưa load xong trang Hồ sơ thành lỗi sai tài khoản (`profile account mismatch`).
  - Phải có cơ chế tự động gửi `KEYCODE_BACK` thoát Camera/Overlay và điều hướng lại Profile chuẩn qua `tap_navigation_target`. Nếu recovery thất bại, trả về `profile_verify_status = "camera-recovery-failed"` và fail-closed, tuyệt đối không dùng XML camera cũ để đối soát username.
- **Loại bỏ hoàn toàn Touch Gesture khi đóng Android Notification Shade:**
  - Để đóng thanh thông báo che TikTok (`com.android.systemui`), chỉ dùng lệnh non-touch `cmd statusbar collapse`. Tuyệt đối không dùng `input swipe` từ đáy màn hình vì sẽ có nguy cơ chạm trúng nút `[+]` tạo video của TikTok. Polling kiểm tra focus nếu sang app lạ thì fail-closed ngay lập tức.

## Mode 2 structural proof and regression discipline (session 2026-08-13)

### Evidence thật từ UI dump
- Profile identity: node `com.ss.android.ugc.trill:id/sf5` chứa exact `@uid`; dùng helper canonical `automation_core.tiktok.profile.profile_identity_from_xml(xml)` rồi strip `@` và so sánh chính xác. Không suy identity từ display name/header.
- Populated follower list: structural marker `com.ss.android.ugc.trill:id/u5r` + exactly one selected semantic relation header. Header toàn màn hình như `Đã follow 26` là tab/stat, **không phải** relationship proof.
- Explicit-empty follower surface may omit `u5r`: require exactly one selected `android:id/text1` relation header total and it must be exact supported `Follower 0`, plus unique known ViewPager, empty-title, non-empty message and illustration markers. A second selected Following/Friends/Suggested header is ambiguity and must reject.
- Follower row: username nằm ở `txt_desc`; action inline là clickable `tcj` (`Follow`/`Follow lại`). Classify action phải scoped vào đúng row/control; text cùng từ ở nơi khác không được tính.

### Invariants fail-closed cần pin bằng regression
- Sau tap inline, nếu row vẫn `Follow`/`Follow lại` qua bounded retry thì **escalate Path B ngay**, không block trước khi thử profile proof. Path B chỉ classify sau khi đồng thời thấy marker list `u5r` đã biến mất và exact profile identity khớp UID đích.
- Path B phải luôn back/restore follower list trong cleanup, kể cả wrong/missing identity, unknown action, not-followed, hoặc exception. `not_followed` trên profile mới set global `FOLLOW_BLOCKED`; identity/action/restore unknown → `MANUAL_REVIEW`, không suy diễn success.
- `_scroll_follower_list=False` là navigation failure, không phải end-of-list; cả nhánh list rỗng/no-pending và post-batch đều phải `MANUAL_REVIEW` với reason actionable.
- List follower structurally rendered nhưng zero row là trạng thái hợp lệ; `_open_follower_tab` chấp nhận list proof độc lập với row count, sau đó loop bounded idle-scroll.
- `run_mode2` phải return incoming `SessionResult` unchanged khi status đã khác `OK`; không load/shuffle seed, navigate hoặc mutate state sau Mode 1 `MANUAL_REVIEW`/`CONFIG_ERROR`.
- `mode=both`: Mode 2 vẫn xử lý seed đã có Mode 1 state, nhưng `budget_per_session` dùng chung và trừ follow đã tiêu ở Mode 1. Follow đầu Mode 2 bắt buộc Path B; cadence sampling sau đó phải tính theo follow ordinal thật.
- Unknown row action fail-closed; back-to-feed chỉ giữa các seed, không giữa follower trong cùng list.

### Cách viết regression đúng branch
- Với stale-inline→Path-B: queue XML theo thứ tự `list before → tất cả inline retries vẫn Follow → exact @uid profile + scoped action → restored list`; assert outcome, block state, back count và queue consumption. Trước patch phải fail vì production block sớm, không được fail do queue/harness.
- Với leave-list/identity: tách test marker `u5r` còn tồn tại, identity thiếu, identity sai, action ngoài scoped control/header giả, restore-list fail. Mỗi test mutate một điều kiện và assert không tap/follow success.
- Với orchestration: spy `_open_follower_tab`/navigation và state snapshot để chứng minh incoming non-OK không có side effect; monkeypatch scroll fail ở cả hai call site, không chỉ assert một nhánh.
- Sau worker edit, AST-compare toàn bộ top-level `test_*` với checkpoint; từng có worker xóa test/lồng `def`, tạo RED `UnboundLocalError`. Đó là harness corruption: restore checkpoint byte-for-byte, không tính TDD evidence.

## Worker coordination
- Dispatch multiple Codex workers can cause conflicts: one worker reverts another's changes. Use `write_file` (direct rewrite) instead of `patch` when file keeps getting reverted. Or kill active workers before dispatching new one.
- After Codex returns, always dispatch Claude to review actual code before telling user anything. Do not ask user mid-loop.

## TikTok UI selector bugs (session 2026-07-27)
- **`find_by_fields` exact-match trap**: `resource_id=""` chỉ match element có resource-id rỗng. TikTok element thường có `resource-id="com.ss.android.ugc.trill:id/..."` → dùng `resource_id=None` để bỏ qua filter này. Tương tự, `content_desc` exact match không khớp với content-desc động như `"Follow <username>"` → dùng prefix match `desc.startswith("Follow ")`.
- **`already_following` false positive**: `find_by_fields(text="Đã follow")` match nhầm tab navigation "Đã follow" thay vì nút follow của user. Phải thêm `element.clickable` để phân biệt.
- **Follow rate logic trap**: Tab Following/Friends toàn người đã follow → không ai để follow nữa. Đặt follow rate > 0% cho các tab này là vô nghĩa; phải = 0%. Chỉ For You mới có người lạ để follow.
