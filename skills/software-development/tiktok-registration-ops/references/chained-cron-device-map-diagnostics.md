# Chained Cron + Device-Map Diagnostics

Use for Gmail → TikTok night-chain failures where Telegram reports only `exit code 1` or truncated output.

## Evidence path

Trace the exact run: Hermes cron job → `night_chain_reg_pipeline_launcher.py` → `run_night_chain_pipeline.py` → canonical Gmail `run_all.ps1` → `logs_parallel_<timestamp>` → `summary.json`/`summary.txt` → per-machine logs. The aggregate exit code is not the root cause. Report phase, counts, exact signatures, and run artifact path.

## Map source verification

`gmail_reg_v10.py` resolves the map in this order: `GMAIL_DEVICE_MAP_WORKBOOK`, `PROXY_DIENTHOAI_PATH`, then repo-local `data/taikhoan_run_safe.xlsx`. Check the effective environment and file path before assuming config is missing.

`taikhoan_run_safe.xlsx` is a multi-row account view. Build a set of valid serials per machine; never let the last account row overwrite the machine map.

## Date-as-serial corruption

A malformed `Device ID` cell can contain `23/08/2026` or `2026-08-24`. If treated as an ADB serial, logs show `adb.exe: device '<date>' not found`. Ignore Python `date`/`datetime` values and recognized date strings. If more than one valid serial remains for a machine, fail closed with a conflict instead of selecting arbitrarily.

## Safe fix verification

After changing the map loader, do not rerun live registration during diagnosis. Run:

1. focused map tests;
2. `py_compile` and `git diff --check`;
3. read-only loader verification against the real safe workbook, asserting affected machines resolve to the known valid serial and contain no date separators.

Do not edit the workbook unless the user explicitly asks for data repair. Do not report the cron as broken when the canonical child runner created fresh batch artifacts.

## Reporting style

Answer directly in Vietnamese: distinguish “cron/runner đã chạy” from “batch target fail”; give the actual error class and artifact. Avoid dumping full logs or secrets. If the user asks to fix, state whether the fix is code seam, config, or workbook data before acting.
