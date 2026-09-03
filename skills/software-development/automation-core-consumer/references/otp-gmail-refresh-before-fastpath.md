# otp-gmail refresh-before-fast-path fix (social_reg_v1.py, audit F1)

Session: 2026-08-07. Task A (MINOR_FIXES audit) edited the `_try_get_otp_gmail_app`
flow in `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` so Gmail pulls/refreshes its inbox
BEFORE reading any OTP fast-path.

## Finding (F1)

Two "fast paths" read OTP code from a UI XML captured BEFORE a pull-to-refresh:
- Fast-path 1 read code from the currently-open conversation XML, captured right
  after launching Gmail (before entering the mailbox / any refresh) → stale /
  no code.
- Fast-path 2 (`extract_recent_tiktok_otp_from_gmail_list(xml_mailbox,...)`)
  read the preview from `xml_mailbox` captured at
  `_ensure_gmail_mailbox("after account switcher")` — also before refresh.
- The actual `_gmail_pull_refresh(1)` call lived at ~7143, AFTER both fast paths,
  and worse was a silent `NameError` (see nested-def rule in SKILL.md) so it
  never ran.

## Fix applied (exact order)

1. **Moved helper defs up.** `_gmail_text_stats`, `_gmail_snapshot`,
   `_gmail_pull_refresh` were relocated to just after `_ensure_gmail_mailbox`
   (before the flow). Their old copies further down were deleted. Now a call at
   the new site actually binds to the def.
2. **Deleted stale fast-path 1** (the "read code from already-open TikTok
   conversation" branch) — its root XML is pre-mailbox/pre-refresh by
   construction. Kept `current_is_conversation` (still needed by the back-nav
   below: "return to inbox before opening avatar").
3. **Moved the refresh before fast-path 2:**
   ```
   xml_mailbox = _ensure_gmail_mailbox("after account switcher", save_proof=True)
   if not xml_mailbox: return None
   try:
       xml_mailbox = _gmail_pull_refresh(1)     # NOW refreshes the mailbox
   except Exception as refresh_exc:
       log(...)
   # then extract_recent_tiktok_otp_from_gmail_list(xml_mailbox, ...) — refreshed xml
   ```
4. Kept the second (idempotent) `_gmail_pull_refresh` later at "before
   refresh/search" — now actually functional once defs are above.

## Verification

- `python -c "import ast; ast.parse(open('social_reg_v1.py', encoding='utf-8').read())"`
  → OK.
- `file social_reg_v1.py` → CRLF line terminators preserved.
- `git diff --check social_reg_v1.py` → clean.
- Real pytest targets (`tests/test_login_method_entry.py`,
  `tests/test_gmail_otp_marker_node_fix.py`, `tests/test_hotmail_mail_die_alive_guard.py`)
  must be re-run after the edit — do not skip verification because the edit was
  scripted.

## Diff footprint

127 lines changed in `social_reg_v1.py` (59 insertions / 68 deletions), mostly
the def move + fast-path 1 removal + refresh relocation.