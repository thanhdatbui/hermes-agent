# WorkbookTotpProvider — reusable 2FA TOTP from workbook

Module: `login_runner/totp_provider.py` (consumer repo `tiktok-login-vpn-preflight`)

## Purpose

Reads the 2FA column from the tracking workbook, generates a current TOTP code via `pyotp`,
and returns it to the executor's `submit_challenge()` flow.

## Usage in cli.py

```python
from login_runner.totp_provider import WorkbookTotpProvider

executor = LoginExecutor(
    ...
    challenge_provider=WorkbookTotpProvider(args.proxy_mapping, secret_provider),
    ...
)
```

## How it resolves the workbook row

1. `request_code(job, "2fa")` is called by `LoginExecutor._execute_locked()`
2. Provider reads `identifier` from `secret_provider.get_login_secret(job.secret_ref)`
3. Opens workbook via `openpyxl.load_workbook(path, read_only=True, data_only=True)`
4. Finds row by `(machine, identifier)` matching
5. Reads the 2FA column (aliases: `2fa`, `totp`, `two factor`)
6. Returns `pyotp.TOTP(secret).now()` (6-digit code)

## Cache

Results are cached per `(machine, secret_ref)` for the session lifetime.
A single `WorkbookTotpProvider` instance can serve multiple login jobs.

## Dependencies

- `pyotp` (must be installed: `pip install pyotp`)
- `openpyxl` (already a dependency of automation-core)
