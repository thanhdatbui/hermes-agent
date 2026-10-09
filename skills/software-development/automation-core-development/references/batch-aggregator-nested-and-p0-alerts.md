# Batch Aggregator: Nested Run Dirs, Summary Fallback, P0 Auth Alert, and Runner Hooks

## Context
When running large-scale farm jobs (TikTok feed sessions, Gmail batch registration) across dozens of physical or emulated devices, execution results and failure artifacts must be aggregated to detect systemic failures versus sporadic noise without causing alert fatigue.

## 1. Heterogeneous Run Directory Layouts
Different runners organize machine artifacts differently:
1. **Root Multi-Machine Manifest**:
   - Location: `<run_dir>/run_manifest.json`
   - Key: `multi_machine_summary` (list of dicts).
   - Fields: `serial` / `machine`, `final_status` / `status`, `blocker_type` / `error_type`, `stop_reason` / `reason` / `error_message`, `artifact_root`.
2. **Standard Machine Subdirs**:
   - Location: `<run_dir>/machines/<serial>/run_manifest.json`.
3. **Nested Timestamp Subdirs**:
   - Location: `<run_dir>/machines/<serial>/<timestamp>/run_manifest.json`.
   - Occurs when runners create per-run timestamp folders under each machine's output directory. Loaders must scan 2-levels deep if direct subdirectories do not contain manifests.
4. **Direct Job Folders**:
   - Location: `<run_dir>/<job_dir>/run_manifest.json`.

## 2. Text Summary Fallback & Artifact Recovery
- When `run_manifest.json` does not include `error_type` or `error_message`, check `summary.txt` in the manifest's parent directory:
  - Match prefixes: `status:`, `final_status:`, `stop_reason:`, `reason:`.
- Image snapshot fallback:
  - If `snapshot_png` or `snapshot_xml` paths are not in the manifest, look for `*<serial>*.png` or `*.png` / `*.xml` in the manifest or `artifact_root` directory.

## 3. P0 Severity Bypass for Dual-Threshold Systemic Detection
- **Dual-Threshold Rule**: By default, an error signature only triggers a batch alert if:
  `failures_in_signature / total_machines >= min_rate (default 10%)` AND `failures_in_signature >= min_count (default 3)`.
  This prevents Telegram notification spam on sporadic network drops or transient timeouts.
- **P0 Critical Bypass**:
  - Keywords: `login`, `account screen`, `verification`, `checkpoint`, `auth`, `văng`, `switch_reason`, `identity`.
  - When an error signature matches these auth/login-critical keywords, the dual-threshold requirement is bypassed (`should_alert = True` immediately).
  - Rationale: A single checkpoint or account eviction event can signal an account ban wave or unexpected UI displacement across the farm, requiring immediate canary inspection.

## 4. Runner Hook Placement Pattern
- **PowerShell Multi-Worker Runners** (e.g. `run-feed-session.ps1`, `run_parallel.ps1`):
  - Place aggregator hook after batch completion, before resource/lock cleanup (`Release-QueuedReservations`), or immediately prior to exit.
  - Always encapsulate hook calls in `try { ... } catch { Write-Warning "batch_aggregator hook error: $_" }` so that an aggregation or network issue never obscures the runner's exit status.
  - In `run-feed-session.ps1`, resolve target batch directory appropriately if root manifest or nested machine folders exist.
