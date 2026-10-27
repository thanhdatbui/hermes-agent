# Case Study: Hermes Cron Engine no_agent=True Contract & Spend-Guard Drift

## 1. Problem Context
An unpinned cron watchdog (`hourly-stale-post-receipts-reconcile`, `8d6b3c18dd64`) suddenly stopped executing and fired an error alert on Telegram:
```text
⚠️ Cron 'hourly-stale-post-receipts-reconcile' failed: Skipped to prevent unintended spend:
global inference config drifted since this job was created (model 'omni-worker' -> 'ag-gemini-pool-3'),
and this job is unpinned. No inference...
```

The operator queried: `"Clgt"` (What the f*** happened?).

## 2. Root Cause Analysis
1. **Unintended Spend-Guard Mechanism in Hermes Scheduler:**
   - In `cron/scheduler.py` (around line 3110), Hermes evaluates:
     ```python
     _model_snapshot = (job.get("model_snapshot") or "").strip().lower()
     if _model_snapshot and not (job.get("model") or "").strip():
         _current_model = str(model or "").strip().lower()
         if _current_model and _current_model != _model_snapshot:
             _drift.append(f"model '{_model_snapshot}' -> '{_current_model}'")
     if _drift:
         raise RuntimeError(f"Skipped to prevent unintended spend: global inference config drifted...")
     ```
   - When an agent prompt cron job (`no_agent: false`) is registered without explicitly pinning a `model`, Hermes captures the current model as `model_snapshot` (e.g. `omni-worker`).
   - If the user or environment switches the global model (e.g. to `ag-gemini-pool-3`), Hermes halts the job to prevent accidental billing on the new provider/model.

2. **Architectural Misconfiguration:**
   - Watchdogs and cleanup tasks (`cron_reconcile_stale_receipts.py`) should NEVER be configured as LLM Agent jobs.
   - An LLM agent invocation for a simple file cleanup consumes prompt tokens on every tick and creates a failure dependency on model availability and configuration stability.

3. **Hermes Script Path Contract:**
   - Hermes cron enforces that the `script` parameter MUST be a relative filename resolving under `~/.hermes/scripts/` (which resolves on Windows to `%LOCALAPPDATA%\hermes\scripts\`):
     ```text
     Script path must be relative to ~/.hermes/scripts/. Got absolute or home-relative path: 'D:/...'.
     Place scripts in ~/.hermes/scripts/ and use just the filename.
     ```
   - Passing absolute paths (e.g. `D:/Taadaa/tools/...`) will fail validation.

4. **Policy Hook `CRON_AGENT_POLICY_BLOCKED`:**
   - Farm guard hooks enforce `no_agent: true` on cron updates. Attempts to set `no_agent: false` are blocked unconditionally.

## 3. Remediation & Verification Protocol
1. **Convert to `no_agent: true`:**
   ```python
   cronjob(
       action="update",
       job_id="<id>",
       no_agent=True,
       script="cron_reconcile_stale_receipts.py",
       workdir="D:\\Taadaa\\tools"
   )
   ```
2. **Immediate Test Execution:**
   - Trigger the job manually via `cronjob(action="run", job_id="<id>")`.
   - Verify `last_status == "ok"` and `execution_success == true`.
3. **Quarantine Stale Violators:**
   - Run `python D:/Taadaa/tools/reconcile_cronjobs.py --apply` to automatically audit and pause any legacy jobs violating the `no_agent: true` policy.
4. **Trigger Two-Way Sync:**
   - Trigger `cron-sync-watchdog` (`cronjob action='run' job_id='2b5b608429c7'`) to guarantee that `jobs.json` changes persist cleanly across Git deploy and runtime.
