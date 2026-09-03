# Machine-30 reauth OTP + security identity fallback (2026-08-05)

Live session transcript for `susannemortimerabby9@hotmail.com` (row 105, machine 30,
serial `ce0217126cd4bc640c`, SM-G930F, Chrome 138, accessibility OFF).

## Sequence that finally progressed

1. `pm clear com.android.chrome` (user-approved) → killed saved-password sheet + SSO.
2. Chrome first-run onboarding: "Xem thêm" (`com.android.chrome:id/more_button`
   `[594,1728][1008,1872]`, tap ~`(801,1800)`) → "Tôi hiểu" (`[564,1728][1008,1872]`,
   tap ~`(786,1800)`). Later a SECOND interstitial "Quyền riêng tư nâng cao trong quảng
   cáo trên Chrome" with the same button pair.
3. Open `https://outlook.live.com/mail/0/inbox?nlp=1` (WITH `?nlp=1`; without it you get
   the microsoft.com marketing page, often 502 under proxy) → real
   `login.microsoftonline.com` form, `i0116` email field exposed at `(540,607)`.
4. `login(force_login=False)` → SUCCESS; pipeline then reached security reauth.
5. Reauth proof screen "Xác minh danh tính của bạn" on `login.live.com/login.srf?wa=wsignin1.0...`:
   - "Gửi email đến th*****@gmail.com" (recovery = `thanhdatbui1995@gmail.com`,
     `DEFAULT_RECOVERY_EMAIL` in `flows/hotmail_recovery.py`).
   - Buttons "Tôi có một mã" / "Tôi không có bất kỳ thứ gì trong số này".
   - Pipeline failed `security_email_proof_screen_lost_before_submit` because after
     `type_text` + `ime hide` the opaque dump no longer shows the proof screen
     (`flows/hotmail_security.py` line ~1208). Worked around by driving the UI by hand
     (see below) — the flow's own submit path still needs the fix (submit from pre-hide
     xml or coordinate fallback).
6. Manual completion (this is the reusable recipe):
   - Tap blue "Gửi mã" `(841,1316)` (pixel scan: blue band y≈1250-1370 x≈684-1007).
   - Poll `cd "/d/Taadaa/add mail khoi phuc" && OTP_SENDER_HINT="microsoft"
     OTP_LOOKBACK_SECONDS=1800 python read_otp_mail.py --once --verbose` →
     `CODE=260596 FROM=...accountprotection.microsoft.com SUBJECT=Mã bảo mật tài khoản
     Microsoft cá nhân` (mail arrived in ~25-40s).
   - IME was open (`mInputShown=true`); `adb shell input text 260596` + `keyevent 66`.
   - URL → `privacynotice.account.microsoft.com/notice`; tap blue "Tiếp tục"
     `(827,1733)`, re-scan, second tap `(827,1721)` worked → URL
     `account.live.com/password/change`.
7. Pipeline rerun (VPN restart does NOT drop Chrome cookies — login still
   `ALREADY_SIGNED_IN`): reached change-password but failed
   `password_change_target_identity_not_verified` → after opaque fallback added,
   `password_change_target_identity_menu_not_dismissed` (still open at session end —
   `_ui_has_content` was True because of Chrome URL-bar drag hint text
   "ban co the cham va giu đe di chuyen thanh đia chi xuong duoi cung").

## Code changes made this session (uncommitted at session end)

- `flows/hotmail_login.py`:
  - `CHROME_CHROME_IDS` extended: `toolbar_button`, `drag_handlebar`, `url_bar_editor`,
    `search_box_text`, `window_toolbar`, `tab_switcher_toolbar`, `bottombar`,
    `bottom_toolbar`.
  - New `SYSTEMUI_IDS = ("com.android.systemui:", "android:id/",
    "com.android.systemui:id/")` — SystemUI nodes frequently have NO `package`
    attribute (only resource-id), so the package filter misses them. Filter resource-id
    by these prefixes in BOTH `_ui_has_content` and `visible_flat_text`.
  - `login()` first-step predicate + inbox-first branch accept `has_outlook_inbox_url`
    (opaque URL proof) — this moved the pipeline from `LOGIN_NOT_VERIFIED` to
    `ALREADY_SIGNED_IN`.
  - `visible_flat_text` now filters non-Chrome packages + SystemUI ids.
- `flows/hotmail_security.py`:
  - Import `_ui_has_content` from hotmail_login.
  - `_verify_target_identity_before_logout`: opaque fallback — if
    `_ui_has_content(xml) is False` and `_active_url(xml).endswith("/password/change")`,
    accept identity (URL proof; page only reachable via verified target session).

## Open issue at session end

- `password_change_target_identity_menu_not_dismissed`: the opaque fallback did not
  trigger because `_ui_has_content` returned True due to the Chrome URL-bar drag-hint
  text node (no resource-id matched the filters). Need to identify that node's
  class/resource-id and add it to `CHROME_CHROME_IDS` or another filter, or special-case
  the hint text. Then re-run pipeline to complete change-password + logout-devices.
- Test count at session end: 37 passed (test_hotmail_login.py), 136 passed + 3 subtests
  (full suite).
