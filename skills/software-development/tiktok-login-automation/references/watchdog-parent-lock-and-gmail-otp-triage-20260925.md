# Watchdog Login Triage: Parent Lock and Gmail OTP (2026-09-25)

## Incident pattern
A watchdog acquires a device lock for a machine and then invokes `tiktok_login_v1.py` as a child process. The child also calls `acquire_device_lock()`. If the child is not explicitly configured to inherit the parent lock, it returns `exit=2` at the device-lock gate before the login flow begins.

## Required diagnosis order
1. Read the watchdog's exact subprocess command and the child script's lock-handling branch. Confirm whether `--allow-parent-lock` is passed and whether the parent project is in `PARENT_LOCK_PROJECTS`.
2. Do not interpret `exit=2` as a password/OTP failure until the child log is read. In `tiktok_login_v1.py`, `DeviceLockNeedsUserDecision` is an explicit `return 2`; the VPN gate also returns `2` on a preflight block; a normal unsuccessful account flow can also return `2` after `PENDING LOGIN`.
3. Use the target run's fresh log window, not historical lines from the shared append-only `social_reg_log.txt`. Capture the exact timestamp and correlate it with the watchdog output. If the watchdog uses `capture_output=True` but discards `stdout/stderr`, treat the root reason as unobserved until the child log is correlated.
4. For Gmail OTP accounts, inspect the same-attempt Gmail XML/screenshot. Distinguish:
   - target account absent from Gmail account switcher;
   - target account selected but Gmail stuck on loading (`Đang nhận thư của bạn…`);
   - target selected with a warning/action-required state;
   - TikTok OTP not delivered or expired.
5. Only after the evidence supports it, classify the blocker as lock, VPN, Gmail mailbox, TikTok auth, or post-login verification.

## Evidence from this incident
- The tracking inventory showed `@annhubvqttr` mapped to `an.nhuan.work64541@gmail.com` with `issues=missing_tiktok_pass`; this is a durable account-data condition, not proof of a live login failure.
- A later Gmail artifact `debug_gmail_switcher_missing_an.nhuan.work64541_gmail.com_190453.xml` contained the actual text `Đang nhận thư của bạn…` and a Gmail loading progress bar. The corresponding log window reported four failed account-list checks followed by `khong co trong Gmail account list sau retry`.
- An earlier log window for the same email showed Gmail selected the target account and then `Timeout chờ login success`, so do not merge that earlier flow with the later watchdog attempt without timestamp matching.
- `dumpsys account` can show the Google account exists in Android AccountManager while Gmail still cannot present/select/sync it. OS account presence is not proof that Gmail OTP retrieval is usable.

## Watchdog implementation pitfall
If the parent lock is intentionally inherited, the child invocation must pass `--allow-parent-lock`, and the parent project must be accepted by the child's whitelist. If the watchdog project is not whitelisted, changing only the flag is insufficient; the contract must be updated deliberately and tested. The watchdog must also preserve the child's stdout/stderr or print a structured reason, otherwise it reports only `exit=2` and hides the actionable cause.

## Reporting format
Respond briefly and directly:
- `Nguyên nhân đã xác nhận`: quote the exact log/XML line.
- `Bằng chứng`: timestamp + artifact path.
- `Chưa xác nhận`: any competing `exit=2` branches not eliminated.
- `Hành động tiếp theo`: one bounded, evidence-backed next step.

Never state that the parent-lock bug or Gmail warning caused the specific watchdog attempt unless the exact attempt's child log proves it. Multiple historical runs may have different causes.
