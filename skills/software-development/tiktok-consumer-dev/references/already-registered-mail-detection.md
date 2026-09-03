# Already-registered mail: TikTok login-existing but no tracking row (2026-08-05)

## The trap

The eligibility detector (`scripts/tiktok_target_eligibility.py`) selects a
source mail as a registration target when its TikTok ID is blank in
`taikhoan_dat_v2_updated .xlsx`. That is correct for the normal pipeline, but
it does NOT prove the mail is unregistered on TikTok:

- A source mail whose TikTok account was created outside this pipeline (other
  tool, older run, manual) has NO tracking row even though TikTok already
  knows the address.
- At runtime the flow enters "email đã có tài khoản" → existing-account LOGIN
  (OTP/verify) instead of registration. For Gmail the login path then spends
  the OTP budget on a mailbox that may not even carry a fresh code →
  `GMAIL_OTP_TIMEOUT` / `OTP_REJECTED_NO_FRESH_CODE`, and the target is burned
  without creating anything.

Live example STT 31: `lynnehansenafnkh@gmail.com` had no row in tracking
(rows for machine 31 held only `zewududkmn@hotmail.com` → `lu.huyn926` plus
empty slots), yet TikTok answered with the existing-account login flow. The
mail could NOT be registered again.

## How to confirm before treating a mail as a registration target

1. Detector says target → run once.
2. Watch the worker log: `→ detected: OTP/verify screen → email DA CO tai
   khoan, login tiep` / `dang o OTP/verify → di tiep flow login` means the
   mail ALREADY has a TikTok account.
3. Cross-check tracking manually:
   ```python
   # any row where GMAIL column == this mail (casefold)
   # if none, the account is external to this pipeline
   ```
4. Also compare machine rows: the mail may belong to a DIFFERENT machine's
   slots than the source STT says.

## The fix (user-approved policy)

A source mail that is confirmed already-registered (login-existing at
runtime) must be REMOVED from `gmail_clean_v2.xlsx` so the detector stops
picking it. Use the same guarded source-deletion path as CAPTCHA cleanup —
`social_reg_v1.remove_captcha_dead_email_from_source(email)` — WITH the
writer env set (see `tiktok-reg-batch-runner.md` workbook-write section),
which creates a backup and reopen-verifies. Never delete the tracking row
(the account isn't in it). After deletion, re-run the detector: the machine
falls through to its next unused source mail (STT 31 → `macthuong...`).

## Why the OTP/login path burns without the source fix

- Login-existing for Gmail routes to Gmail OTP retrieval with a 150s
  deadline; mailbox verification can succeed (`mailbox check ... reason=ok`)
  while no 6-digit code exists (stale magic link gets skipped) → timeout.
- The recovery runner gives one fresh attempt, then `FINAL_BLOCKED` and the
  target is done for that signature. So a wrongly-selected mail wastes the
  whole machine slot for the batch.

## Note for future: don't conflate with mail-die

`MAIL_DIE_GOOGLE_RELOGIN_REQUIRED` (Audit Pending) is a DIFFERENT
classification — that's a Google session that needs re-login, not an
already-registered address. Keep the two source-removal paths separate.
