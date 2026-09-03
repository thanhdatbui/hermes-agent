# FINAL_BLOCKED fleet diagnosis — recovery-new-handler (2026-08-07)

Sessions: "kiểm tra 35 máy FINAL_BLOCKED sau mấy ca schedule" (root-cause breakdown) and the
follow-up on machines 19/45/49/50 flagged `TARGET_EMAIL_ALREADY_REGISTERED`.

## Interpretation rule (user-confirmed 2026-08-07)

**FINAL_BLOCKED = the script run failed or preflight refused. It is NOT a TikTok ban on the
machine/account.** Machines still open TikTok normally; the script never completed its flow.
When the user says "bọn nó bị block bởi script này chạy fail" — that's exactly right: the
blocker label describes WHERE the run stopped, not that the account is blocked. Two blocker
families:
- `NEW_HANDLER_FAILURE:<signature>; exit_code=1` / `PROCESS_EXIT_1` → child script crashed at a step.
- Preflight refusals (`TARGET_EMAIL_ALREADY_REGISTERED`, `TARGET_SERIAL_MAPPING_CHANGED`,
  `TRACKING_SLOT_BLOCKED`, `DEVICE_LOCKED`, `NO_HANDLER_IMPLEMENTED`) → never touched the device.

## Active runtime root (CRITICAL)

`Tiktok_Reg/project_paths.py`:
```python
RUNTIME_ROOT = Path(os.environ.get("TIKTOK_REG_RUNTIME_ROOT",
    str(Path(os.environ.get("LOCALAPPDATA") or PROJECT_ROOT/".runtime")/"Taadaa"/"Tiktok_Reg")))
ARTIFACT_ROOT = RUNTIME_ROOT / "artifacts"
```
As of 2026-08-07 the ACTIVE root was the project-local `.runtime`:
`D:\Taadaa\Tiktok_Reg\.runtime\Taadaa\Tiktok_Reg\artifacts`
The `%LOCALAPPDATA%\Taadaa\Tiktok_Reg\artifacts` copy was STALE (last runs 2026-08-04).
`search_files`/`rg` on `D:/Taadaa` also failed (path form) — use `cd /d/Taadaa && rg …` in bash instead.

## Aggregation snippet

```python
import json, glob, collections
agg = collections.defaultdict(list)          # stt -> [(run, blocker)]
for f in glob.glob("*/recovery_summary.json"):
    run = f.split("/")[0]
    try:
        s = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    for stt, t in s.get("targets", {}).items():
        if t.get("status") == "FINAL_BLOCKED":
            agg[stt].append((run, t.get("blocker", "")))
# per machine: normalize blocker = b.split(";")[0].strip() (strips "; exit_code=1")
# filter entries where run >= "20260806" for the current schedule window
```

Summary JSON shape per run: `run_id`, `target_count`, `status_counts`, `targets[stt]` =
`{status, final_state, blocker, attempts, workbook_write}`, `launch_plan` (seed/order/delays).

Union across ALL runs (both roots) 2026-08-03→07: 31 machines —
1, 4, 6, 10, 16, 18, 19, 21, 30, 31, 32, 33, 34, 36, 38, 39, 40, 45, 47, 49, 50, 52, 54, 55, 57, 62, 63, 64, 66, 70, 72.

## Machine breakdown (2026-08-06 → 2026-08-07)

| stt | type | blocker (normalized) | root cause from stdout |
|---|---|---|---|
| 34 | gmail | PROCESS_EXIT_1 x19, TIKTOK_STARTUP_NOT_FOREGROUND x3, GMAIL_OTP_TIMEOUT x2, VPN_RECOVERY_FAILED x2 | **OTP fetched → screen gone on return** (`[otp-enter] TikTok OTP screen unavailable after Recents recovery`). 29 runs, 0 success. Device left on Gmail ConversationList. |
| 57 | hotmail | PROCESS_EXIT_1 x8, CAPTCHA x1 | **Same OTP-screen-lost** via Outlook CDP (`[otp-cdp] Fresh Outlook code found in background tab` → return → OTP screen gone, reset to SignUpOrLoginActivity). |
| 66 | hotmail | PROCESS_EXIT_1 x9 | **Same OTP-screen-lost** via CDP. |
| 31 | gmail | GMAIL_OTP_TIMEOUT x12 | Gmail opened correct account/inbox, refresh x2 + search `from:noreply@tiktok.com` → candidates=0, 150s timeout. Email never arrived or unreadable. |
| 54 | hotmail | HOTMAIL_OTP_TIMEOUT x6 | `RECOVERY_OTP_SCREEN_NOT_IDENTIFIED` — Outlook web inbox not confirmed, no OTP. |
| 30 | hotmail | PROCESS_EXIT_1 | Retry loop: `[preflight] TikTok already foreground; bounded force-stop/relaunch recovery` → `[04_add_account] Không tìm thấy 'Thêm tài khoản'`. Was SUCCESS on 06-08 11:06, regressed. |
| 36 | gmail | GMAIL_TARGET_ACCOUNT_NOT_LISTED x4 | Email not in Gmail account list → GMAIL_RECOVERY_CAPTCHA → account DELETED from gmail_clean (SKIPPED_GMAIL_ONLY). Machine lost its target email. |
| 55 | gmail | GMAIL_TARGET_ACCOUNT_NOT_LISTED x1 | Same as 36. |
| 39 | gmail | DEVICE_NOT_PROVISIONED | `NO_HANDLER_IMPLEMENTED:DEVICE_NOT_PROVISIONED` — no provisioning handler registered; not retryable. |
| 38 | hotmail | ADB_TRANSPORT_RECOVERY_FAILED | Transport loss during startup/UI capture; proxy reassign + bounded soft reboot failed; LOCK_RETAIN_FAILED. |

Other machines (old runs, 03-08/04-08, mostly `%LOCALAPPDATA%` root — check `stt_XX/attempt_*/stdout.log`):
- 6, 10, 16, 72: `[otp][OTP_REJECTED_NO_FRESH_CODE]` — Gmail has mail but no fresh code.
- 18: `[06_email_option] icon_count_0` — email icon not found on login screen.
- 19/45/49/50: `TARGET_EMAIL_ALREADY_REGISTERED` — preflight refusal, see section below.
- 21: device lock active (never ran).
- 32/33: `RESUME_PRECONDITION_FAILED: expected=password_required; observed=otp_required`.
- 40: `[otp-enter] TikTok OTP screen unavailable after Recents recovery` (same screen-loss).
- 47/52: `[gmail-health] target mailbox not verified`.
- 62: `[01_open] TikTok not foreground after clean launch` (stuck on launcher).
- 63/64/70: `GMAIL_RECOVERY_CAPTCHA` — stuck on `MinuteMaidActivity` (GMS phone verify).
- 1/4: `PROCESS_EXIT_2` early death, no detailed log (batch 03-08).

Historic batch 2026-08-03 (31 machines, `%LOCALAPPDATA%` root, `social-batch-all/20260803-115823`):
~22x `[03_dropdown] Không mở được account dropdown`, ~5x `[01_open] TikTok not foreground after clean launch`,
1x `[adb-timeout]` on serial ce11160bd0119a1203.

## TARGET_EMAIL_ALREADY_REGISTERED (19/45/49/50)

- Where: `scripts/run_tiktok_recovery_new_handler.py` `_build_items` (~633), BEFORE any device work:
  `elif _norm_email(email) in registered: item.blocker = "TARGET_EMAIL_ALREADY_REGISTERED"`.
  `registered = social.load_registered_tiktok_emails(tracking)` = emails whose tracking row has
  non-empty Tik ID (col C). Handler refuses to run; machine never opened.
- **These machines are NOT in the current `_clean_targets.json`** (as of 2026-08-07 active targets:
  30, 34, 36, 38, 39, 54, 55, 57, 66). So the flag is stale — they were not scheduled again, not
  failing repeatedly.
- Workbook evidence (taikhoan_dat_v2_updated .xlsx, header: Máy/Tik/ID/PASS/2FA/GMAIL/PASS MAIL/
  NGÀY SINH/NGÀY TẠO/device ID): machines 19/45/49/50 each have multiple registered accounts
  WITH TikTok password (col D) and mail password (col G); some rows have 2FA (col E). Rows with
  empty col C = unused slots (e.g. 150/357/358/389/390/397/398). One row (385 hiencao179) had ID
  but EMPTY pass TikTok — needs manual fix before login.
- If the reg script DID run an already-registered email, TikTok never "goes straight in": it shows
  either a **password field** (`registered` → `fill_password_and_login`, types col D pass, reveals
  via eye icon, taps login) or an **OTP screen** (`registered_otp` → `[7c]` fetches code from
  inbox: Gmail app for gmail targets, Outlook web/CDP for hotmail targets). Non-preferred
  registered emails are skipped via BACK. Detection order in `detect_after_continue` (~1651):
  password field → OTP hints → "da co tai khoan" text → "tai khoan khong ton tai" (→new) →
  login-form markers → new-reg hints (birthday/"tao tai khoan").

## Signature → verdict mapping (used this session)

- `[otp-enter] Cảnh báo: không còn ở màn OTP` → screen-preservation bug; OTP WAS obtained.
- `[otp-enter] TikTok OTP screen unavailable after Recents recovery` → same; STOPPED.
- `[otp-gmail] TIMEOUT at search loop after 150s` + `candidates=0` → email never arrived; distinct from screen-loss.
- `[preflight] TikTok already foreground; bounded force-stop/relaunch recovery` in consecutive runs → retry loop on a stuck machine.
- `GMAIL_TARGET_ACCOUNT_NOT_LISTED` + `DELETED_AND_VERIFIED` → account removed from source; machine no longer has a valid target.
- Check live device with `adb shell dumpsys activity activities | grep mResumedActivity` — run may have died while the phone sits on Gmail/launcher.

## Lesson

Machine stuck in the OTP-screen-lost loop cannot succeed while the bug exists — re-running
every 10–15 min burns the attempt cap and churns locks. Diagnose the screen-preservation
root cause (TikTok resetting to SignUpOrLoginActivity on Recents return) before re-enabling runs.
