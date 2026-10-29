# Cron Picker Manifest Failure & StatePaths Feed Workbook Trap

## Problem Description & Symptoms
- **Symptom**: The entire farm cluster (e.g., Kibe Machines 1–80) remains completely idle all morning (e.g., past 07:30 AM) with zero live run directories created under `runtime/<cluster>/live/<today>`.
- **Root Cause**: The staging picker cronjob (`phase9-staging-picker`, running at 06:00 AM via `tiktok_picker.py`) exits with code 1, failing to generate `ACTIVE.json` and the daily manifest (`assignment-v1-*.json`). Downstream runners (`tiktok_runner.py`) check for active manifests and exit silently when absent.

## Technical Failure Mechanism
1. **`StatePaths.regular_file` Validation Contract**:
   Inside `python_runner/hermes_cron/models.py`, `StatePaths.regular_file(path)` enforces strict containment and extension policies:
   ```python
   target = target.resolve()
   if self.offline_root != target and self.offline_root not in target.parents:
       raise ValueError(ReasonCode.INVALID_PATH.value)
   if target.suffix.lower() in {".xlsx", ".xls", ".csv", ".tsv"}:
       raise ValueError(ReasonCode.INVALID_PATH.value)
   ```
2. **The `env.json` Workbook Injection Pitfall**:
   If `<repo>/runtime/hermes-cron/env.json` defines:
   ```json
   "HERMES_CRON_FEED_WORKBOOK": "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx"
   ```
   `tiktok_picker.py` forwards `--feed-workbook <path>` to `hermes_cron_picker.py`.
   Line 54 attempts `workbook_path = paths.regular_file(args.feed_workbook)`, which immediately raises `ValueError: INVALID_PATH` because the workbook is located in OneDrive (outside `offline_root`) and has the forbidden `.xlsx` extension.
3. **`sys.path` Missing in Standalone CLI Runner**:
   When `hermes_cron_picker.py` is invoked as a subprocess script (`python.exe python_runner/scripts/hermes_cron_picker.py`), `sys.path[0]` is `python_runner/scripts`. Without an explicit repository root prepended to `sys.path`, `from python_runner.hermes_cron.models import ...` raises `ModuleNotFoundError: No module named 'python_runner'`.

## Prevention & Remediation
1. **Rely on Synchronized Source Config**:
   Remove `"HERMES_CRON_FEED_WORKBOOK"` from `env.json`. The picker then branches to `--source-config`, reading the pre-validated JSON file (`cron-source/hermes_cron_source_config.json`) synchronized automatically by `taikhoan-run-safe-sync`.
2. **Self-Contained Module Path Bootstrap**:
   In `python_runner/scripts/hermes_cron_picker.py`, ensure the repo root is bootstrapped before importing package modules:
   ```python
   _repo_root = str(Path(__file__).resolve().parent.parent.parent)
   if _repo_root not in sys.path:
       sys.path.insert(0, _repo_root)
   ```
3. **Active Manifest Conflict**:
   If a manual probe runs the picker directly and creates a manifest, running subsequent picker commands with a different seed without `--force-regenerate` raises `ACTIVE_MANIFEST_CONFLICT`. Once `ACTIVE.json` exists in `runtime/<cluster>/cron-state/manifests/<today>/`, verify its status and trigger `phase9-runner-tiktok-feed` directly.
