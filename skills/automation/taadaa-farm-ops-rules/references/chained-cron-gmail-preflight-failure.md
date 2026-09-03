# Chained Gmail -> TikTok Cron: Evidence Pattern

## Purpose

Use this reference when a no-agent night-chain cron reports `exit code 1` or `Cron failed` and the operator asks whether the scheduled Gmail registration actually ran.

## Read-only diagnosis sequence

1. Identify the exact cron job ID and scheduled run timestamp.
2. Inspect the launcher chain statically:
   - Hermes launcher -> `run_night_chain_pipeline.py`
   - Phase 1 -> canonical `register gmail/run_all.ps1`
   - Phase 2 -> TikTok runner
3. Locate the run-specific Gmail artifact directory, not the shared historical log. For this project the usual root is `D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_<timestamp>`.
4. Read `summary.json`, `summary.txt`, `machine_launch.json`, and per-machine logs. Redact email addresses, passwords, OTPs, tokens, and serials in the user-facing report.
5. Verify whether a fresh TikTok phase artifact directory exists. If no new TikTok artifact exists, do not claim TikTok UI/OTP failure; classify the result as launcher/preflight/phase-gating failure.
6. Report Phase 1 and Phase 2 independently. A wrapper's final non-zero code is only the aggregate status.

## Durable interpretation rules

- A fresh `logs_parallel_<timestamp>` directory proves `run_all.ps1` was called and entered the Gmail runner; it does not prove any account succeeded.
- `summary.json` with `total=15`, `success=0`, `failed=15`, `failed_other=15` means the Gmail batch ran and all selected targets failed. The exact per-machine reasons must come from `machines[*].reason` and worker logs.
- Repeated `[BLOCKED][PRE_GMAIL][APP_STARTUP] repeated after one recovery` is a Gmail preflight/device-state blocker, not evidence that cron skipped the script.
- `proxy readiness timed out` and ViChanger `GET_IP failed after 3 retries` are proxy/VPN preflight failures; keep them separate from Gmail UI startup failures.
- An ADB error where the device identifier is a date-like value such as `23/08/2026` or `2026-08-24` is strong evidence of a device-map/serial extraction or workbook-column issue. It is a data/mapping anomaly to audit before retrying, not a normal device-offline conclusion.
- A phase can produce a normal summary and still return non-zero. The chain's `exit 1` is explained by the phase return code; always cite the phase summary counts and exact signature instead of only repeating `exit 1`.

## Operator-facing report shape

Use short Vietnamese sections:

- `Kết quả`: whether the scheduled script ran and whether it succeeded.
- `Lỗi gốc`: exact phase and error signatures, grouped by class.
- `Bằng chứng`: run-specific artifact paths and summary counts.
- `Blocker`: what remains unresolved.

Do not run the batch, probe devices, repair workbooks, or modify launchers during a read-only diagnosis unless the operator explicitly expands scope.
