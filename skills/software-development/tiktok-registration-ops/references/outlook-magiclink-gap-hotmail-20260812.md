# Hotmail/Outlook Magic-Link Gap in TikTok Reg — Root Cause & Fix Plan (2026-08-11/12)

## Gap Discovered (STT30 2026-08-11, confirmed 2026-08-12 máy 66)

**Symptom:** Hotmail email `DaunteHoffeditz56902@hotmail.com` already has TikTok account.
- Script detects `email DA CO tai khoan` at step 07 → goes to OTP login flow (correct)
- But Outlook numeric reader returns **OLD rejected code** → `OTP_REJECTED_NO_FRESH_CODE`

**Root Cause:** `prefer_magic_link` flag ONLY propagated to Gmail reader (`_try_get_otp_gmail_app`).
Hotmail/Outlook readers (`_try_get_otp_outlook_cdp`, `_try_get_otp_browser`, `_try_get_otp_outlook_newest`)
**ignore the flag entirely** → treat magic-link screen as OTP screen → try to enter 6-digit code.

## Current Code Flow (Broken for Hotmail Magic-Link)
```python
# handle_tiktok_email_otp ~L10678+
if prefer_magic_link:
    # Gmail only!
    return _try_get_otp_gmail_app(..., prefer_magic_link=True)
else:
    # Hotmail numeric path — NO magic-link guard!
    code = _try_get_otp_outlook_newest(...)
    enter_otp_code(device, code)  # FAILS on magic-link screen
```

## Fix Plan (Audit-Approved, Not Yet Implemented)

### 1. Propagate `prefer_magic_link` + `not_before` to ALL readers
```python
def _try_get_otp_outlook_newest(device_id, email, password, *, stt=None, timeout=240, 
                                prefer_magic_link=False, not_before=None):
    if prefer_magic_link:
        return _read_outlook_magic_link_with_evidence(device_id, email, password, stt=stt)
    # ... numeric path
```

### 2. Fail-closed for Hotmail magic-link (blocker MUST come before env-gated resend)
```python
# In handle_tiktok_email_otp, Hotmail branch:
code = _try_get_otp_outlook_newest(..., prefer_magic_link=prefer_magic_link)
if code is None or code == "MAGIC_LINK":
    if code == "MAGIC_LINK":
        return "MAGIC_LINK"  # success
    # None = no evidence → FAIL CLOSED
    raise RuntimeError("OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED")
```

### 3. `enter_otp_code` guard: reject magic-link screens before ANY tap
```python
# At top of enter_otp_code:
flat = strip_accents(xml).lower()
if any(m in flat for m in MAGIC_VERIFY_HINTS):  # "kiem tra hop thu", "gui lai email"
    raise RuntimeError("OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK")
```

### 4. NEWEST-MAIL EVIDENCE REQUIREMENT
- Must open Outlook inbox (verified XML)
- Find TikTok row with **time evidence** (timestamp token in DOM)
- Open THAT specific row (not first match)
- Extract code from opened message body
- `exclude_codes` list (rejected codes) MUST be respected — never return stale code

### 5. Test Coverage
- `test_hotmail_magic_link_unverified_blocks_regardless_of_resend_env`: parametrize env `{None,"1","0"}` → always raises `OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED`
- `test_outlook_newest_mail_reader_returns_none_when_no_row`: inbox without TikTok row → None
- `test_outlook_newest_mail_reader_taps_correct_row`: 2 mails → taps newest (time evidence) → reads code from opened mail

## Evidence from This Session
- Máy 66: Hotmail email with pre-existing TikTok → `FINAL_BLOCKED OTP_REJECTED_NO_FRESH_CODE`
- Log: `[otp-newest] Fresh code found in newest TikTok mail: [REDACTED]` → rejected → resend → same code returned → `reader returned a previously rejected code; refusing reuse`
- Outlook inbox verified but newest-mail reader still returned stale code (same DOM row, not refreshed properly)

## Related Files
- `social_reg_v1.py`: `handle_tiktok_email_otp` (~L10678), `enter_otp_code` (~L10215), `_try_get_otp_outlook_newest`
- `references/outlook-magiclink-gap-stt30-20260811.md` (full audit doc)
- `tests/test_login_outlook_magiclink_branch.py` (add tests here)