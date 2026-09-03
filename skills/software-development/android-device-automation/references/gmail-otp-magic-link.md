# Gmail OTP / Magic-Link Reading — TikTok Registration (S7 farm)

Consumer: `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (function `_try_get_otp_gmail_app`
and helpers). Shared flow `run_google_live_check` lives in
`automation_core/google_health.py` and the repo `D:\Taadaa\add mail khoi phuc`.

## TikTok sends a MAGIC LINK, not a 6-digit OTP

- Screen: "Kiểm tra hộp thư của bạn / Bạn có thể đăng nhập bằng liên kết được gửi
  đến <email>" with a "Đăng nhập bằng mật khẩu" link underneath.
- **This screen means the email ALREADY has a TikTok account** (login flow, not
  fresh registration). Do NOT keep searching for a 6-digit code in the mailbox —
  that path times out.
- Correct handling (already in consumer): open the email in the Gmail app, no
  6-digit code found → tap the confirm/verify/link button inside the message →
  return `"MAGIC_LINK"`. Caller treats it as success (login proceeds via the link).
- If "Đăng nhập bằng mật khẩu" is visible, the account exists; the source
  workbook (`gmail_clean_v2.xlsx` col `pass mail`) holds the MAIL password, NOT a
  TikTok password — the two are separate workbook columns (`PASS` vs `PASS MAIL`)
  and may differ. A missing TikTok password means you cannot log in by password;
  use the magic link instead.

## Gmail search-loop bugs (fixed 2026-08-06) — avoid regressions

1. **Search query order**: specific `from:` queries FIRST
   (`from:noreply@account.tiktok.com`, `from:noreply@tiktok.com`), generic
   (`verification`, `code`, `TikTok`) LAST. Generic "TikTok" matches the search-bar
   text itself and empty-state text → false "has result".
2. **Empty state guard**: a search result page containing "Không có kết quả phù
   hợp cho TikTok" (or `hub_empty_text`) contains the word "tiktok" — must NOT be
   treated as a hit. Otherwise the loop sets `xml3 = xml_search` and spins to the
   150s deadline without trying the next query.
3. **Exhausted queries must break**, not `continue` — when all search queries have
   been tried with no result, return instead of looping until deadline.
4. **Search view ≠ wrong account**: in Gmail search view the selected-account disc
   (`selected_account_disc_gmail`) is hidden, so `_gmail_mailbox_state` reported
   `target_account_unverified` and the loop re-opened the inbox forever. Detect
   `open_search_view_edit_text` / `search_suggestion` / `hub_empty_text` and treat
   as valid Gmail (`reason=ok`). A REAL wrong account still yields
   `target_account_not_selected` (correct — different email shown).
5. **`ignore_timestamp`**: email in Promotions may carry an old timestamp but a
   fresh code. For the Promotions fast-path pass `ignore_timestamp=True` (still
   honoring `exclude_codes`). Default stays timestamp-guarded.

## Auto-sync OFF is a real root cause for "no mail"

- Samsung S7: `settings put global auto_sync 1` does NOT stick; `dumpsys content`
  keeps reporting `auto sync: u0=false`. The Gmail app adapter may also show
  "Tính năng tự động đồng bộ hóa đang tắt".
- Symptom: inbox empty, every `from:` search returns `candidates=0`, pull-to-refresh
  shows nothing → `GMAIL_OTP_TIMEOUT`.
- Enabling reliably requires the Settings UI (Accounts → Google → account → sync),
  not adb. Don't fight it via adb settings.

## When OTP read fails → run the Gmail LIVE CHECK (user-mandated)

- On `GMAIL_OTP_TIMEOUT` the flow must NOT just declare timeout — it must probe
  the account: open the Google account manager surface and classify via
  `run_google_live_check` (LIVE / CAPTCHA / PHONE_VERIFY / RELOGIN). Consumer
  helper: `_gmail_account_live_probe(device_id, email, stt)`.
- Only HEALTH_CAPTCHA / identity blocker justifies deleting the source row;
  PHONE_VERIFY maps to HEALTH_MANUAL (keep mail, manual handling).

### Classifier gap: identity-verification gate must map to IDENTITY_BLOCKER (dead)

A homegrown live-probe classifier that only checks `recaptcha`/captcha-xml can
report `NORMAL_ACCOUNT` for an account that is actually CAPTCHA-dead, because
Google renders the gate as an **identity-verification** screen, not a reCAPTCHA.
Symptoms on machine 31: `_gmail_account_live_probe` → `NORMAL_ACCOUNT` while the
add-mail repo flow (`check_google_live_with_core`) correctly raises
`BlockedAccountRecaptchaDelete: Google identity verification / reCAPTCHA gate
after relogin`. The screen shows "Xác minh thông tin để tiếp tục" (accounts.google.com).
- Markers that must classify to `GoogleLiveState.IDENTITY_BLOCKER` (match the
  add-mail repo `_classify_screen_state`):
  `xac minh danh tinh cua ban`, `de bao mat tai khoan cua ban`,
  `verify your identity`, `xac minh thong tin de tiep tuc` (+ `is_google_manual_blocker_xml`).
  Check them BEFORE the phone-verify branch and before the "com.google.android.gm
  in xml → LIVE" fallback — otherwise the gate screen misclassifies as LIVE.
- **Lesson**: when the consumer's live-probe verdict disagrees with the proven
  repo's verdict, trust the proven repo and port its classifier markers — don't
  trust the simpler one.

## CAPTCHA-dead mailbox: the canonical delete flow (add-mail repo, verified 2026-08-07)

Full sequence for "OTP không về → check mail live → CAPTCHA → xóa khỏi máy + excel"
(what the user demands instead of just timing out):

1. `rar.check_google_live_with_core(serial, gmail, pass_mail)` — opens the Google
   account manager surface, runs the state machine. Raises
   `BlockedAccountRecaptchaDelete` on identity/CAPTCHA gate.
2. `rar.cleanup_blocked_captcha_account({'gmail': ...}, so_may, reason)` — device
   removal via `remove_blocked_google_account_from_device` + workbook backup/delete
   via `backup_delete_account_from_workbook` (writes a `.before-remove-<acct>.xlsx`
   backup, sha256-verified). Logs
   `SUMMARY machine=31 account=... device=REMOVED_AND_VERIFIED gmail_clean=DELETED_AND_VERIFIED taikhoan_dat_v2=NO_MATCH`.

### Pitfall: MACHINE_DEVICES int vs str keys → silent None device → DEVICE_NOT_PROVISIONED

`run_add_recovery.MACHINE_DEVICES` (fallback hardcoded map) has **int keys**
(`31: "ce04..."`), but `cleanup_blocked_captcha_account` passes `so_may` as a
**string** `'31'`. `MACHINE_DEVICES.get('31')` → `None` → the cleanup callback
runs `remove_blocked_google_account_from_device(None, ...)` → core fails
`DEVICE_NOT_PROVISIONED` (device is None), leaving a misleading
`[captcha-delete] DEFERRED device=REMOVE_FAILED`. The `dumpsys account` check in
the error path also reports "Không xác định được account đích" even though the
account IS present. Fix:
`MACHINE_DEVICES.get(int(so_may)) if str(so_may).strip().isdigit() else MACHINE_DEVICES.get(so_may)`.
- Diagnostic shortcut: `rar.MACHINE_DEVICES.get(31)` works but
  `rar.MACHINE_DEVICES.get('31')` is None → int/str mismatch confirmed.

## Machine already logged into an existing account

- `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` happens when the
  device is already logged in (profile shows `@handle` in the dropdown, no
  "Add account" button). The flow expects a logged-out device.
- Check the workbook before assuming a fresh reg: an email can already have a
  TikTok account that was never written to the workbook (Tik rows left empty).
  The visible `@handle` in the profile is often that account — verify, then write
  the tracking row (Tik = next empty slot) instead of re-registering.
- **Do NOT assume the visible @handle belongs to the target email** — on machine
  34 the device was logged into `@skiperenok`, an account belonging to someone
  else entirely (user: "k phải của tao"). Verify with the user / workbook before
  writing anything.

## Device-bound existing session survives pm clear (S7) — factory reset is the only escape

On Samsung S7, an already-logged-in TikTok account **cannot be removed via adb**:

- `pm clear com.ss.android.ugc.trill` → session still there after relaunch
- `settings delete secure android_id` + `pm clear com.google.android.gms` → still there
- `rm -rf /data/data/com.ss.android.ugc.trill/{files,shared_prefs,databases}` → still there

TikTok binds the session to the device server-side (firmware-level ID beyond
adb reach). TikTok 46.x profile UI also exposes **no Settings/Add-account button**
in the a11y tree (only "Chia sẻ"/"Thông báo" top-right), so UI logout via tap is
not scriptable either. If the bound account is not yours, the ONLY clean path is
`adb shell recovery --wipe_data` (factory reset) + re-provision (proxy, APK).
Confirm with the user first — reset loses all accounts/config on that machine.

### Google AssistedSignInActivity overlay

After TikTok data-clear on a machine with Google accounts, the app relaunch can
land on `com.google.android.gms/.auth.api.credentials.assistedsignin.ui.
AssistedSignInActivity` **overlaid on the TikTok profile** — blocks
`[02_profile]`/`[04_add_account]` and the flow fails with
`TIKTOK_STARTUP_NOT_FOREGROUND`. Dismiss with BACK key (`input keyevent 4`);
it can reappear on every relaunch while the stale session exists.

## Core version merge (user-mandated, 2026-08-07) — DONE

User directive: "merge các phiên bản core lại cho đầy đủ fix all lỗi chứ, merge
check conflict trùng" + "đẩy qua automation core" — the atx-kill fix must live in
**automation-core source**, not as a venv cherry-pick that is lost on every wheel
reinstall.

**COMPLETED 2026-08-07** — the merge is done and pushed:
- Source `automation-core` already had atx-kill (`ui.py` `ATX_AGENT_PROCESS_MARKER`)
  but had REMOVED the old transport-recovery API
  (`AndroidTransportRecoveryError`, `MissingVpnRecoveryError`,
  `recover_android_transport`, `recover_missing_android_vpn`) that
  `Tiktok_Reg/scripts/run_tiktok_recovery_new_handler.py` imports.
- The 4 symbols + 2 result dataclasses (`MissingVpnRecoveryResult`,
  `AndroidTransportRecoveryResult`) were ported VERBATIM from the 0.4.32 wheel
  (pip-cache `...\wheels\8b\a3\35\0c0582aa...\automation_core-0.4.32-...whl`) into
  `src/automation_core/device_recovery.py`. Signature note:
  `__init__(serial, state_path, reason)` — positional, NOT kwarg-only `state_path=`.
- Version ladder: **0.4.41** (expected_marker param) → **0.4.42** (legacy API merged)
  → **0.4.43** (pkill -9 SIGKILL in `_recover_uiautomator`).
- After installing a new wheel, DELETE stale `automation_core-*.dist-info`
  directories (they accumulate: 0.4.31/32/38/41/42) — `importlib.metadata`
  reports the OLDEST one while the code files are the newest, causing phantom
  "version mismatch" / wrong-version reports. Keep only the current dist-info.
- Runner gate: bump `REQUIRED_CORE_VERSION` in `run_tiktok_recovery_new_handler.py`
  to match the installed core, else `AUTOMATION_CORE_VERSION_MISMATCH:expected=...;actual=...`
  at import.
- **Build gotcha**: `python -m build` is absent in the Hermes venv — use
  `pip wheel . --no-deps -w dist` instead.
- **Whole-file `git add` trap**: the working tree had ~2870 lines of uncommitted
  changes from OTHER work in `social_reg_v1.py`; `git add social_reg_v1.py`
  committed them all (2871 insertions). Check `git diff --stat` scope BEFORE
  staging when a file was already modified at session start (31 modified files
  listed in the workspace snapshot).

## Device state after runs

- uiautomator frequently wedges after a run (`EXIT=137`) → `pkill -f atx-agent`
  (see main SKILL.md pitfall). Only reboot when that doesn't recover.
- After reboot: VPN via watcher / `vi_changer_vpn` START_VPN broadcast; verify
  `tun0` has an inet address before running the reg runner.
