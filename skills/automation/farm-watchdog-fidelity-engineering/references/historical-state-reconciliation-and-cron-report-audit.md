# Historical State Reconciliation & System-Wide Cron Report Audit

## 1. Context & The "Fixed Code, Forgotten State" Anti-Pattern
On large-scale automation farms (e.g. 1040 Hotmail/Gmail profiles across Kibe M01-M80 and Admin M201-M280), operations execute through layered pipelines:
1. **Runner Scripts** (`chatgpt_gpm_direct_reg.py`): Execute browser UI actions per account.
2. **Supervisors** (`batch_gpm_5profiles_supervisor.py`): Manage concurrency, inspect returncodes, and persist state (`batch_gpm_5profiles_supervisor_state.json`).
3. **Periodic Watchdogs & Reports** (`cron_hotmail_gpm_lifecycle_6h_report.py`): Aggregate state files and emit digests to Telegram.

### The Trap
On 2026-10-26, a critical bug was resolved in `chatgpt_gpm_direct_reg.py`:
- Previous bug: The runner returned exit code `0` when candidates were empty (due to missing `PASS CHATGPT` column in Admin workbooks).
- Supervisor inspected `returncode == 0`, marked `chatgpt_registered_at = now()`, and advanced 564 Admin accounts to `WAIT_7D` -> `DONE` without ever registering.
- The fix on 2026-10-26 corrected the CLI exit codes, added password normalization fallback, and fixed `/about-you` UI onboarding.
- **The Failure:** The engineer stopped after fixing the code and verifying tests. **Historical state files (`batch_gpm_5profiles_supervisor_state.json`) were never reconciled.**
- **The Consequence:**
  - The 6h report continued broadcasting "ChatGPT Reg Thành Công: 567/630 (92.3%)".
  - Operators were misled into believing registration was almost complete.
  - The supervisor never re-queued these 500+ accounts for registration, starving the farm of real ChatGPT accounts while advancing un-registered accounts into security credential modification (`CHANGE_INFO` / `DONE`).

---

## 2. The Mandatory Reconciliation Protocol
Whenever a bug fix addresses phantom success, missing validation, or corrupted state transitions:

### Step 1: Ground-Truth Triangulation
Never trust JSON state timestamps alone. Cross-check against external source-of-truth registries:
- **Registry / DB Check:** Query the active provider connections table in OmniRoute (`SELECT email FROM provider_connections WHERE provider='chatgpt-web' AND is_active=1`).
- **Credential Existence:** Check if the account has an actual generated/stored password (`raw.get("chatgpt_password")`).

### Step 2: Atomic State Reconcile Script
Run an automated, reversible reconciliation script:
1. Create a timestamped backup: `state.json.bak_YYYYMMDD_HHMMSS`.
2. Categorize profiles into `GENUINE` vs `PHANTOM`:
   - `GENUINE`: Exists in OmniRoute connection pool OR has valid credentials.
   - `PHANTOM`: Has `chatgpt_registered_at` timestamp BUT missing credentials AND absent from connection registry.
3. Reset `PHANTOM` records:
   - Clear phantom timestamps: `chatgpt_registered_at = None`.
   - Revert stage to the pre-requisite step: `stage = "CHATGPT_REG"`.
   - Preserve genuine progress (`HOTMAIL_LOGIN` timestamp, device bindings, retry counts).
4. Save state atomically and trigger a report refresh.

---

## 3. System-Wide Cron Report Audit Checklist
When reviewing or hardening farm reporting watchdogs, verify the following 4 structural integrity checks:

### 1. Dual-Cluster Inventory Parity
- **Risk:** Scripts like `cron_gmail_gpm_2fa_6h_report.py` hardcoding Kibe paths (`master_gmail_manager.xlsx`, Group 10) and completely omitting the Admin cluster (M201-M280).
- **Rule:** Every farm-wide report MUST either explicitly loop over both clusters (`kibe` + `admin`) or clearly scope itself in the title (e.g. `[KIBE ONLY]`).

### 2. Host Target Identity Protection
- **Risk:** Relying on `os.environ.get("USERNAME")` for target cluster detection (e.g. `farm_render_download_watchdog.py`). When running on Kibe, it defaults to monitoring Kibe even if scheduled to monitor Admin.
- **Rule:** Explicitly pass cluster target via CLI arguments (`--cluster admin`) or dedicated config files, never relying on ambient OS username alone.

### 3. Balanced Silent Watchdog Behavior
- **Risk:** Complete silence for 6h/12h when 0 new events occur causes operators to question if the cron scheduler died.
- **Rule:** On nominal zero-event intervals, emit a concise 1-line heartbeat or enforce an end-of-day summary, reserving full suppressions only for high-frequency (5-minute) pollers.

### 4. Heartbeat Coverage Completeness
- **Risk:** `cron_heartbeat.py` monitoring a legacy static set of 8 watchdogs while 30+ new autonomous watchdogs run unmonitored.
- **Rule:** Periodically audit `cron/jobs.json` and sync all active watchdogs into the 24h health aggregator spec.
