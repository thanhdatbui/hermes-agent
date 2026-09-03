# Batch recovery, lock integrity, and OTP field safety

Use this reference for a failed multi-machine registration run.

## Recovery sequence

1. Read the authoritative `all_results.json` from the exact run that exited. Build the retry set from its `FAILED_*` rows only; do not infer the set from screenshots, an older manifest, or a truncated console tail.
2. Group failures by signature: account dropdown/add-account, UI XML/ATX timeout, OTP/login-success timeout, rate-limit, proxy/ADB, and unknown/no artifact.
3. Confirm the current device serial from the authoritative inventory workbook and verify ADB plus per-device VPN/proxy readiness before touching the device.
4. Preflight the **same lock root used by the runner and cron**. A lock in a backup, quarantine, archive, or alternate runtime directory is not an operational lock. Never delete or overwrite an active lock just to make a retry start.
5. Pause only the cron jobs that can select, run, sync, reap, or otherwise alter the target devices/workbooks. Record their IDs and restore them after the goal is complete.
6. Reserve every retry target atomically before starting the first child. Keep `queued` locks for waiting targets and `running` locks for active targets. Failed targets remain `recovery`/`handoff`/`blocked` with artifacts; they are not silently released.

## OTP/password guard

Before entering a code, validate the current TikTok package and the target field using UI semantics (OTP label, six-code layout, resource/class, and focused field). Never use a generic first `EditText` fallback. If the field cannot be distinguished from password, stop that target, preserve the screen and lock, and save a screenshot/UI dump. OTP entry uses the tested non-sensitive/direct input path for the six-cell visual OTP field; password entry must only occur after an explicit password-field check.

## Failure handling

- Known mechanical failures: use the existing handler (resend code, refetch Graph OTP, dismiss keyboard popup, retry dropdown, resume or restart only when the handler requires it), recapture, and cap meaningful attempts at two per signature.
- Rate-limit markers such as `Bạn truy cập dịch vụ của chúng tôi quá thường xuyên`, `Too many attempts`, or `Too many requests` require a 48-hour cooldown artifact and exclusion by target detection; do not hot-retry.
- Unknown screen, CAPTCHA, persistent ADB/proxy failure, conflicting workbook mapping, or missing artifacts are handoff blockers. Report the machine, serial, exact error signature, screenshot/UI dump path, and attempts.
- A successful child is not a successful registration until its verified result JSON contains the TikTok ID and proof XML/screenshot. Deferred batch runners do not write the tracking workbook automatically; apply and verify deferred results separately.

## Evidence checklist

For each target record: run ID, STT, serial, source email redacted where appropriate, initial state, action/handler, attempt number, post-action state, result JSON, proof screenshot/XML, lock decision, and final lock state. Do not report a batch as complete from `SUCCESS` console lines alone.
