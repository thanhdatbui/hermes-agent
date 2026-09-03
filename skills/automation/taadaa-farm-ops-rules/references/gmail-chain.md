# Gmail -> TikTok chained cron diagnosis

Use for no-agent cron reports of `exit code 1` or `Cron failed`.

## Read-only path

1. Anchor the exact job ID and run timestamp.
2. Trace Hermes launcher -> `run_night_chain_pipeline.py` -> canonical Gmail `run_all.ps1` -> TikTok runner.
3. Inspect the fresh `D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_<timestamp>` directory, especially `summary.json`, `summary.txt`, `machine_launch.json`, and per-machine logs. Do not rely on shared historical logs.
4. Verify whether a fresh TikTok artifact directory exists. If not, do not infer a TikTok UI/OTP failure.
5. Report Gmail and TikTok phases independently; the wrapper exit code is aggregate only. Redact credentials, OTPs, tokens, emails, and serials.

## Interpretation

- A fresh `logs_parallel_*` directory proves `run_all.ps1` was invoked and the Gmail runner entered execution; it does not prove success.
- `total=15, success=0, failed=15, failed_other=15` means Gmail ran and all selected targets failed. Group exact reasons from `machines[*].reason` and worker logs.
- `[BLOCKED][PRE_GMAIL][APP_STARTUP] repeated after one recovery` is a Gmail startup/preflight blocker, not a skipped cron.
- `proxy readiness timed out` and ViChanger `GET_IP failed after 3 retries` are proxy/VPN preflight failures and must stay separate from Gmail UI failures.
- ADB reporting a date-like device identifier such as `23/08/2026` or `2026-08-24` indicates a likely device-map/serial extraction or workbook-column anomaly; audit mapping before retrying.
- A phase may write a normal summary and still return non-zero. Cite phase counts and exact signatures, not only `exit 1`.

## Report shape

Use short Vietnamese sections: `Kết quả`, `Lỗi gốc`, `Bằng chứng`, `Blocker`. During read-only diagnosis do not run the batch, probe devices, repair workbooks, or modify launchers without explicit scope expansion.
