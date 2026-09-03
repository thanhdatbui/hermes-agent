# Live change-info: preflight, fail-closed new-password gate, and read-only verification (2026-08-21)

Condensed from a live retry of two change-info targets (machine 30 `susannemortimerabby9@hotmail.com`, machine 54 `eulaliaphilomenaclementina7@hotmail.com`) that hit a hard blocker because `HOTMAIL_NEW_PASSWORD` was absent from the agent shell.

## What happened

- User requested a live retry of two machines, with device locks already held in `C:\Users\Kibe\.codex\device-locks\` (v2 protocol: `machine_30.lock.json` + `serial_ce0217126cd4bc640c.lock.json`, `status":"running"`, `owner_active":true`, `lock_id` unchanged).
- Before any live action, verified: lock files present + match machine/serial; `HOTMAIL_NEW_PASSWORD` absent (`PW_ABSENT`, `PW_LEN=0`); `OTP_MAIL_USER`/`OTP_MAIL_APP_PASSWORD` present (OTP mailbox configured).
- Ran a SAFE read-only inventory (no `--live`, no password) to confirm mapping:
  - `machine-30-row-104` → email `susannemortimerabby9@hotmail.com`, `age_days=31`, `eligible=true`, `status=ELIGIBLE`.
  - `machine-54-row-188` → email `eulaliaphilomenaclementina7@hotmail.com`, `age_days=31`, `eligible=true`, `status=ELIGIBLE`.
- Did NOT launch `--live`: without `HOTMAIL_NEW_PASSWORD` the flow fails closed at `NEW_PASSWORD_MISSING` (line 1085) before any serial/VPN/lock step, or hangs on `getpass` under `--live`. Reported `FINAL_BLOCKED / NEW_PASSWORD_MISSING (SECRET_NOT_PROVISIONED)` for both machines, left all locks intact.

## Why this is durable (control-flow proof)

`flows/hotmail_change_info.py`:

- `cli()` line 1923: `new_password = None if args.resume_logout_only else _new_password_from_env_or_prompt(live=True)`.
- `_new_password_from_env_or_prompt` (675): `value = os.environ.get("HOTMAIL_NEW_PASSWORD")`; if empty and `live` → `getpass.getpass("Mật khẩu Hotmail mới: ")`.
- `run_target` (1085): `if not new_password and not resume_logout_only: fail("FINAL_BLOCKED", "NEW_PASSWORD_MISSING")`.
- 1085 is BEFORE `_resolve_serial` (1122), `enable_mapped_vpn` (1137), and `acquire_fn`/lock (1173). So the gate is fail-closed and side-effect-free on the device — a missing secret cannot change any password or disturb locks.

## Preflight checklist (run before every live change-info)

1. `if [ -n "$HOTMAIL_NEW_PASSWORD" ]; then echo PW_PRESENT; else echo PW_ABSENT; fi` → must be PW_PRESENT.
2. `echo "$OTP_MAIL_USER"` present (recovery OTP mailbox, `thanhdatbui1995@gmail.com`).
3. Read-only inventory (above) confirms the locked target's machine/serial/eligibility. Locks untouched.
4. Only then launch live, one machine at a time (OTP shared):
   `PYTHONPATH=. D:/Taadaa/python-envs/automation/Scripts/python.exe flows/hotmail_change_info.py --machine <N> --email <addr> --device <serial> --full-scope-takeover --live`
5. Verify `VERIFIED_SUCCESS` + `password_changed=true` + success marker; else `FINAL_BLOCKED` with `failure_signature` + artifact path.

## Gotchas

- `HOTMAIL_NEW_PASSWORD` is NOT auto-injected; if the user says "use the env var if provided", they mean export it in the agent shell first. No loader file exists in the repo.
- `new_password == target.current_password` → `NEW_PASSWORD_UNCHANGED` (also fail-closed). Supplied password must differ.
- Read-only inventory returns `ELIGIBLE` even without the secret — eligibility ≠ runnability. The password gate is a separate, later check.
- Never print the password/OTP/token in the report. Never release the device lock at end of a retry.
