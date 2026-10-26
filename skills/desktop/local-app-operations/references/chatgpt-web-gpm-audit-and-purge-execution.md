# ChatGPT Web GPM Audit & Purge Execution Runbook

When running automated health checks and deactivation purges on ChatGPT accounts hosted across GPM Antidetect profiles (`python D:/Taadaa/tools/login_audit_and_purge_deactivated.py`):

## 1. Concurrency and Execution Lifecycle
- **Safe Batch Size**: Default `--limit 5` (or `--canary` for 2 accounts). Capping at 5 accounts prevents prolonged GPM socket locks and resource contention.
- **Per-Account Latency**: Each profile lifecycle takes 20–30s:
  1. GPM profile launch via local REST API (`/api/v3/profiles/start/<id>`).
  2. CDP attachment to page debugger URL (`http://<host_port>/json`).
  3. ChatGPT auth navigation (`https://chatgpt.com/auth/login`) and email entry.
  4. OTP retrieval with dual fallback: MS Graph API token first, falling back to Outlook Webmail CDP scraping if token expired (HTTP 400).
  5. Post-login UI evaluation (checking `LOGGED_IN_MARKERS` vs `DEACTIVATED_MARKERS`).
  6. Graceful profile stop and Chrome process termination via `_kill_gpm_chrome(host_port)`.

## 2. Timeout & Cron Background Execution Pattern
- **Foreground Timeout Pitfall**: Total runtime for 5 accounts is ~150–240 seconds. A foreground shell command with default 60s timeout will be terminated with exit code 124 (`[Command timed out after 60s]`).
- **Cron One-Shot Runtime Invariant**: Under Hermes cron runner (`hermes -z` / scheduled cron jobs), `notify_on_complete: true` is not supported (`notify_unsupported`).
- **Mandatory Runner Pattern**:
  Always launch in background and block on `process(action='wait')`:
  ```python
  # 1. Launch background
  res = terminal(background=True, command="python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --limit 5")
  # 2. Wait synchronously up to 300s
  process(action="wait", session_id=res["session_id"], timeout=300)
  ```

## 3. Classification & Non-Destructive Invariants
- **Destructive Purge Boundary**: Purge (`omniroute_purge_helper.purge_account`) and state transition to `DEAD_DEACTIVATED` require unequivocal visual/text markers:
  - `account_deactivated`
  - `đã bị xóa hoặc vô hiệu hóa`
- **Transient vs Structural (UNKNOWN)**:
  - Graph API HTTP 400 Bad Request (token expired), OTP retrieval delays, or navigation timeouts are transient and resolve to `UNKNOWN`.
  - Accounts with `UNKNOWN` must NEVER be purged from OmniRoute (`storage.sqlite`) or marked DEAD.
- **Artifacts & Audit Trail**:
  - Audit trail appended to `D:/Taadaa/logs/chatgpt_audit_trail.jsonl` (capped at 10MB).
  - Lifecycle state updated atomically in `D:/Taadaa/runtime/chatgpt_account_lifecycle.json`.
  - Full run report saved to `D:/Taadaa/reports/chatgpt_lifecycle_report.json`.
