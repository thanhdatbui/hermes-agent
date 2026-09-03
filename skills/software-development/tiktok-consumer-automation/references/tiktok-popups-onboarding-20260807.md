# TikTok popup/onboarding + retry pitfalls (2026-08-07, farm SM-G930F/W8, Tik1 batch)

## Popup "Thêm số điện thoại" (account-security onboarding)
- Blocks EVERY tap: ACCOUNT_SWITCHER `Header candidates=0 centers=[]`, WAIT_FEED `dark=1.000`.
- Only a close X exists: content-desc="Đóng", top-right `[936,84][1056,216]`; parent LinearLayout resource-id `p86`. No Skip/Deny button.
- Tap X WORKS and does not break the flow (no composer involved) — this is the correct dismiss.
- Core rule (≥0.4.37): `add_phone_number_vi` markers ("thêm số điện thoại","tăng cường bảo mật","khôi phục tài khoản dễ hơn") → `_desc("Đóng")` + `p86` fallback. Regression test `test_dismiss_popup_closes_add_phone_number_sheet_via_dong_button`.

## Popup "Cho phép TikTok truy cập máy ảnh và micrô" (camera/mic sheet, composer) — TRAP
- Shows EVERY time the composer opens until the runtime permission is granted. UI: title + disabled "Mở cài đặt" + close X (content-desc="Đóng", top-LEFT `[66,138][138,210]`). No Allow button in the sheet.
- **PITFALL: tapping X closes the WHOLE COMPOSER** → lands back on feed → CAPTION_FILL finds no caption field → "Caption field not found via selectors" (3/3 → fail). Do NOT dismiss this sheet via X.
- Correct fix (CONFIRMED live 2026-08-07, machine 74): pre-grant once so the sheet never appears:
  `adb -s <serial> shell pm grant com.ss.android.ugc.trill android.permission.CAMERA`
  `adb -s <serial> shell pm grant com.ss.android.ugc.trill android.permission.RECORD_AUDIO`
  After grant, composer opens clean (dump shows "Thêm âm thanh" + modes, no sheet). Verify: `dumpsys package ... | grep -E 'CAMERA|RECORD_AUDIO'` → `granted=true`.
- Shipped in core **0.4.39**: `automation_core.media_permissions.grant_tiktok_media_permissions` (idempotent, skips already-granted via dumpsys parse — note: parse value AFTER `granted=` split on `,`, not substring search) + auto-grant call in consumer `CONNECT_DEVICE` (`state_machine.py`). Tests: `tests/test_media_permissions.py`.
- Core rule `camera_mic_permission_sheet_vi` (tap X, added 0.4.38) is WRONG for this sheet — treat it as a trap, prefer pm grant. Note this in any consumer workaround: the sheet sits on top of the composer and the only safe action is granting the permission, not closing.

## "Paste action not found" → long-press the caption field (TikTok 46.2.3)
- Flow: broadcast `am broadcast -a clipboard.set -e text <caption>` → dump → tap text "Dán"/"Paste".
- TikTok 46.2.3 does NOT auto-show the paste menu after a clipboard broadcast → the tap finds nothing.
- Fix: **long-press the caption field** (`input swipe x y x y 1200`) → menu Dán/Paste appears → tap it. Implemented as `adapter.tap_long(x, y, duration_ms=1200)` + retry-dump-tap in `_fill_caption_clipboard` (state_machine.py).
- ⚠️ FIXED (2026-08-07): `adapter.tap_long` was added with a stray `)` (SyntaxError)
  + `tap()` raise accidentally collapsed from 2 args to 1 — both fixed, verify PASS
  (`ast.parse` on adapter.py + state_machine.py, consumer import OK via venv-core024).

## Account check pitfall: dumpsys account does NOT list TikTok accounts
- `dumpsys account | grep 'Account {'` shows only Google/IMAP/WhatsApp etc. TikTok accounts use authenticator type `com.tiktok.auth.type` and do NOT appear in that dump. Machine 27 showed only 2 Gmail + 1 hotmail, but the account-switcher UI actually had chaunpnlb0i (active) / skitezrfa3o / hoangvy5328.
- Truth source: open profile → account switcher (dump XML for account rows), or `dumpsys package com.ss.android.ugc.trill` for install state. NEVER conclude "no account" from dumpsys account alone.

## Profile-name onboarding "Đổi Tên" → tap Hủy (cancel) — machine 27 (core ≥0.4.40)
- Screen: "Tên" title, "Bạn chỉ có thể đổi tên một lần mỗi 7 ngày", field "Thêm tên bạn mong muốn" (resource-id `hgh`), Hủy/Cancel top-left `[24,72][161,204]`, Lưu top-right.
- Blocks ACCOUNT_SWITCHER (`Header candidates=0` — profile header never renders) and can block WAIT_FEED after relaunch.
- **Hủy (Cancel) dismisses it — naming is NOT mandatory.** Do NOT type a name; tap Hủy → returns to the profile page (dump then shows `@username`, "Thêm tên", "Hoàn tất hồ sơ của bạn").
- Core rule (≥0.4.40): `profile_name_onboarding_vi` markers ("thêm tên bạn mong muốn","chỉ có thể đổi tên một lần mỗi 7 ngày") → `_text("Hủy")`. Test `test_dismiss_profile_name_onboarding_via_huy`.

## kworker spin → "could not get idle state" persists after pkill — machine 27
- Signature: idle_state_error does NOT clear after `pkill -f atx-agent; pkill -f uiautomator`; `cat /proc/loadavg` > 10; `top -n 1 | head -18` shows `[kworker/u17:N]` at 80%+ CPU (kernel worker thread spin, usually a wedged driver/IO).
- Root cause is hardware/driver — **NOT fixable in code**; `adb reboot` clears it (90s wait, then dump E=0). After reboot re-apply VPN proxy (tun0 gone).
- Diagnose BEFORE burning retry attempts: check loadavg + top when a machine keeps failing WAIT_FEED/OPEN_TIKTOK with idle-state errors after pkill.

## MEDIA_FINGERPRINT_PENDING self-block loop
- The workflow RESERVES the media fingerprint while resolving the video. If the run fails afterward, the `reserved` fingerprint stays → next run fails with `[MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved` before any device action (machine 74, twice).
- Per-retry ritual: delete the `reserved` fingerprint (backup first into `fingerprint-backup_*`) AND the stale locks (`lock-backup_*`), THEN run. Expect the workflow to re-reserve on every run.
- `machine:<n>.lock.json` + `serial_<serial>.lock.json` both live in `C:\Users\Kibe\.codex\device-locks`.

## Manifest owner_id must match TIKTOK_VIDEO_WORKER_ID
- Preflight dies with `AssignmentError` (before creating a batch dir) when the env `TIKTOK_VIDEO_WORKER_ID` differs from manifest `owner_id`. Keep both identical on every retry; easiest is to reuse the same value for both.

## set_proxy "verification failed" is benign right after reboot
- gan-proxy `set_proxy` can raise `VPN connected but Recent Apps/Home verification failed` — but `ip addr show tun0` already has inet → proxy IS applied. Trust `tun0=1`, not the return value/message.

## Workbook "Video Đã Đăng" lags the post-attempt ledger
- Machine 65: workbook said 5, but `idempotency/post-attempts/` had video 6 = `completed` + `ACCEPTED`, fingerprint `verified_success`. Cross-check the post-attempt + fingerprint ledgers before deciding what still needs posting; the workbook is not the source of truth.

## idle_state_error needs the uiautomator-child kill (core ≥0.4.38)
- `uiautomator_idle_state_error` ("could not get idle state") is a DISTINCT wedge from "Killed"/137. atx-agent kill alone does not clear it; the `uiautomator dump` child holds the idle state.
- Core ≥0.4.38 `_recover_uiautomator` pkills BOTH `atx-agent` and the `uiautomator` child (`UIAUTOMATOR_PROCESS_MARKER`). Manual equivalent:
  `adb -s <serial> shell "pkill -f atx-agent; pkill -f uiautomator; am force-stop com.github.uiautomator"` → next dump E=0.
- Machine 27 still wedged again AFTER a run (E=137 at launcher) — pattern: uiautomator can re-wedge mid/late workflow even after reboot; watchdog-style re-kill before each dump-heavy step may be needed (open question).

## Manifest verification ritual (ad-hoc)
- Every new assignment manifest: temp script `hermes-verify-manifest-*.py` under Temp checking schema_version=1, required keys, `machine:\d+` resource format, no duplicates, scope match; delete temp after. Not suite green — ad-hoc only.

## "Post verification: SUCCESS but generic success marker only" → manual profile check (máy 74/10/55)
- Verifier logs `Post verification: SUCCESS` then fails `Post verification blocked: generic success marker only` when the profile tile count didn't increase in time (or tiles are hidden). The post IS published (submission=ACCEPTED) — do NOT re-run the workflow.
- Correct resolution: manual profile check via UI dump / screenshot vision — open TikTok → profile tab → count video tiles vs baseline.
  - máy 10: profile showed 7 tiles (baseline 5) → video 6 posted → update receipt `completed` + workbook 5→6.
  - máy 55: 5 tiles (baseline 4) → video 5 posted → receipt completed + workbook 4→5.
  - máy 74: video 5 post-attempt `verification_pending` + submission=ACCEPTED → receipt completed + fingerprint `verified_success` + workbook 3→5.
- When post-attempt shows ACCEPTED/verification_pending, treat as POSTED; update ledger + workbook, don't burn another batch.

## Machine already at target video count → retry is wasted (máy 27/58)
- Check fingerprint + post-attempt + workbook BEFORE adding a machine to a retry manifest. If it already has `verified_success` for the planned video count, it's DONE — report "đã xong" instead of launching a batch (máy 27/58 had 5 verified videos; retries just re-triggered TikTok onboarding/CPU spin → fail).

## TikTok account truth source = account switcher UI, not dumpsys account
- Confirmed twice: `dumpsys account | grep 'Account {'` never shows TikTok accounts (they use authenticator `com.tiktok.auth.type`). The account switcher UI dump (rows with usernames) is the truth. Machine 27: switcher had chaunpnlb0i (active) / skitezrfa3o / hoangvy5328 while dumpsys showed only Gmail/Hotmail.
