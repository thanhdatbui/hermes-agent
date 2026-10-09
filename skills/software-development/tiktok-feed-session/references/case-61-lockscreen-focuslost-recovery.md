# Case 61 — Lockscreen / Focus-lost Auto-Recovery (2026-09-04)

Session-specific detail for `tiktok-feed-session`. Canonical 5-step recovery
(Inspect → Root cause → Patch → Pytest → Canary) applied to Machine 61
(serial `ce0916096182161a01`, 1440x2560 physical / 1080x1920 override).

## 1. Hiện trường
- Alert gốc: TikTok focus lost + Samsung lockscreen sạc 75% (`Vuốt để mở khóa`,
  `nữa sẽ sạc đầy`).
- Canary run `20260904-173931` baseline `ui.xml` packages =
  `{com.github.uiautomator, com.android.systemui}`, texts = `UIAutomator /
  快捷方式 / 开发者选项...` → **UIAutomator overlay che foreground**, không phải
  lockscreen thuần. Log: `manual-needed / profile username still mismatched
  after switch`, swipes 0/2 → blocker identity-guard khác, ngoài scope lockscreen.
- `wm dismiss-keyguard` trên máy 61 trả exit 0 (non-secure → auto-dismiss được).

## 2. Patch đã áp dụng (commit 86555d5, tree clean)
- `core/classifier.py`: `TIKTOK/PACKAGEINSTALLER/SYSTEM_PACKAGES`,
  `_LOCKSCREEN_RESOURCE_TERMS` (keyguard, lockscreen, lock_icon, lock_pattern,
  lock_pin, lock_password, kg_, cclock, keyguard_clock, emergency_call_button),
  `_LOCKSCREEN_TEXT_TERMS` (VN+EN: swipe to unlock, vuốt để mở khóa, chạm để mở
  khóa, mở khóa, nữa sẽ sạc đầy, until fully charged, sạc hoàn tất, màn hình
  khóa, nhập mã pin/mật khẩu, enter pin/password), `_LOCKSCREEN_PACKAGES`
  (systemui, samsung lockscreen, keyguard). `_has_lockscreen_marker()` +
  `_has_feed_detail_controls()` + hook `detect_uiautomator_overlay` /
  `detect_edit_name_subpage` / `detect_video_editor_overlay`.
- `flows/device_prepare.py`: mở rộng `_parse_keyguard_state`
  (mIsShowing, mDreamingLockscreen, mSwipeLockShowingBeforeTimeout, mSimSecure),
  `_read_screen_dimensions` (lấy match cuối physical|override),+
  `safe_dismiss_keyguard()` (wm dismiss-keyguard + keyevent 82 + swipe
  w/2,h*0.85 → w/2,h*0.35) + `ensure_device_awake_and_unlocked()`.
- `flows/feed_swipe_smoke.py`: `_is_launcher_focus_loss` nhận
  lockscreen/keyguard/uiautomator, `_relaunch_and_poll_tiktok_focus`
  max_polls 3→4 + ensure-unlock + force-stop uiautomator + BACK+monkey retry,
  thêm `uiautomator_app_overlay` vào recover list.
- `flows/calibrate_screens.py`, `flows/observe.py`: gọi
  `ensure_device_awake_and_unlocked` đầu flow.
- `flows/benign_popup_registry.py` + `core/benign_popup.py`: handler
  `uiautomator_app_overlay` pri 98 (BACK + relaunch TikTok).
- Tests mới: `test_samsung_lockscreen_classified_as_lockscreen`,
  `test_ensure_device_awake_and_unlocked`,
  `test_detect_uiautomator_overlay_and_registry_match`,
  `test_foreground_from_output_priorities`.

## 3. Verification
- `pytest test_classifier + test_device_prepare + test_safety +
  test_before_swipe_launcher_recovery` → **118 passed, 5 skipped**.
- Canary `run-feed-session.ps1 -Machines 61 -Row 1 -RecoveryTestSwipes 2` →
  exit 2, manual-needed (profile mismatch), lockscreen path không kích hoạt live.

## 4. Pitfalls (đừng lặp lại)
1. Refactor classifier làm mất `_has_feed_detail_controls` → NameError 20+ tests.
   Fix: định nghĩa hàm trước `classify_tiktok_screen`.
2. Thêm `am force-stop com.github.uiautomator` trong
   `force_stop_and_relaunch_tiktok` làm lệch `adb.shell.side_effect` →
   StopIteration ở 3 tests cũ. Fix: bỏ lệnh phụ, để caller
   (`_relaunch_and_poll_tiktok_focus`) lo overlay.
3. Guard "có TikTok element → return False" trong `_has_lockscreen_marker`
   giết case `test_lockscreen_beats_login_marker`. Fix: bỏ guard, chỉ xét
   package systemui/samsung/keyguard + resource/text terms.
4. Thứ tự `detect_edit_name_subpage` sau camera block đổi reason string làm vỡ
   test cũ. Fix: giữ vị trí cũ ngay sau activity_unavailable.
5. Test `ensure_device_awake_and_unlocked` phải mock đủ 8 calls, gồm cả
   `wm size` → stdout `1080x1920`, nếu không `safe_dismiss_keyguard` ăn thêm
   call và verify fail.
