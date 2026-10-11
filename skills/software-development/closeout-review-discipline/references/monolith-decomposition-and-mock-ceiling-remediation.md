# Monolith Decomposition, Mock Ceiling Remediation & Farm Closeout Invariants

## 1. Monolith Decomposition Mandate (The 80-84/100 Ceiling Trap)
When an agent writes or refactors a feature into a single monolithic script (>400-700 lines) handling multiple concerns (e.g. CLI runner + Browser CDP + OAuth/OTP retrieval + SQLite mutation + Proxy sync + Reporting):
- Closeout Gate (`closeout_gate.py`) on OmniRoute `:20129` (Sol Auditor) consistently deducts Code Architecture points (7-8/10), capping the overall score at **80 - 84 / 100** (below the threshold of `>= 85`).
- **User Mandate (Invariant 11/10/2026)**:
  > *"Tách file đó ra từng script từng việc. Xong cron chỉ việc gọi từng script chạy cho đủ."*
- **Action**: Do NOT repeatedly patch small edge cases inside the monolith hoping to break 85. Decompose immediately into single-responsibility satellite modules:
  1. `_otp_helper.py`: Only handles credential refresh and OTP extraction (Channel 1: Graph API, Channel 2: Webmail CDP fallback).
  2. `_purge_helper.py`: Only handles account matching, SQLite transaction cleanup, and proxy token synchronization.
  3. Orchestrator Runner (`_runner.py` / main script): Thin coordinator (~150-300 lines) iterating profiles, querying state for $O(1)$ skip, calling the helpers, and generating atomic reports.
  4. Cron Watchdog: Executes the thin runner sequentially on schedule.

## 2. Namespace Isolation & Mock Propagation Trap
When extracting functions from a monolithic script into satellite helper modules:
- Existing unit tests that mock the orchestrator module (e.g. `monkeypatch.setattr(main_mod, "OMNI_DB_PATH", tmp_db)` or `monkeypatch.setattr(main_mod.urllib.request, "urlopen", mock_urlopen)`) **will silently fail to propagate** into the helper modules. The helper functions continue accessing their own module-level globals (`omniroute_purge_helper.OMNI_DB_PATH` và `omniroute_purge_helper.urllib.request.urlopen`).
- **Standard Remedy**:
  1. **Dynamic Parameter Overrides**: Helper functions accept optional parameter overrides:
     ```python
     def purge_account(email, omni_url=..., router_url=..., db_path=None):
         db_path = _get_db_path(db_path)
     ```
  2. **Bridge Wrappers in Orchestrator**: The main script imports helpers and defines thin bridge wrappers that explicitly synchronize mocked attributes before delegating:
     ```python
     def purge_account(email, omni_url=..., router_url=...):
         oph.OMNI_DB_PATH = OMNI_DB_PATH
         oph.urllib.request.urlopen = urllib.request.urlopen
         return oph.purge_account(email, omni_url=omni_url, router_url=router_url, db_path=OMNI_DB_PATH)
     ```
  3. **Targeted Helper Tests**: Dedicated unit tests import the helper module directly and mock its own namespace (`tests/test_omniroute_purge_helper.py`).

## 3. Strict Telemetry Redaction Invariant
- Reviewer Sol Auditor severely deducts Telemetry and Farm Safety points if log strings contain interpolated raw credentials, tokens, or OTP codes:
  * VIOLATION: `logger.info(f"[OTP-WEBMAIL] Found OTP in Outlook inbox: {otp}")`
  * COMPLIANT: `logger.info("[OTP-WEBMAIL] Found OTP in Outlook inbox: [REDACTED]")`
- Always verify that all logging statements pass secrets through redaction before submitting to Closeout Gate.

## 4. Atomic File Persistence Pattern
- Direct writes (`with open(file, "w") as f: json.dump(...)`) risk 0-byte or corrupted state if the process is terminated mid-flight (power cut, killed task).
- Always use the atomic write pattern:
  ```python
  tmp_path = f"{target_path}.tmp"
  with open(tmp_path, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
  os.replace(tmp_path, target_path)
  ```

## 5. SQLite Context Manager & Transaction Rollback
- Raw cursor operations without transaction context can leave database state half-mutated if an exception occurs mid-loop.
- Wrap SQLite mutations in `with conn:`:
  ```python
  conn = sqlite3.connect(db_path)
  try:
      with conn: # Automatically commits on success, rolls back on exception
          cur = conn.cursor()
          cur.execute("DELETE FROM provider_connections WHERE id = ?", (target_id,))
          cur.execute("UPDATE combos SET data = ? WHERE id = ?", (new_data, combo_id))
  finally:
      conn.close()
  ```

## 6. Offline Mock Ceiling vs Live Farm Safety Dilemma (Valid L3 BLOCKED)
- Reviewer AI often creates an impossible dilemma:
  * Rubric demands live end-to-end execution logs on real farm browsers/devices to award $\ge 85$ points.
  * Farm Safety Invariant strictly forbids running destructive/live actions or touching physical devices during closeout testing.
  * Strike 3 Hand-Off to Claude CLI may encounter a safety filter refusal (e.g. Anthropic blocking automated 2FA/OTP interception at scale).
- **Escalation Protocol**: When all 16/16 tests pass, atomic writes and transaction rollbacks are verified, architecture is modularized, but the score remains capped at 80-84 due to lack of live farm logs:
  * Do NOT enter infinite retry loops.
  * Conclude with **L3 BLOCKED accompanied by complete verification evidence** (pytest scorecard, mock verification traces, Claude refusal logs). Under Taadaa coordination rules, a verified L3 BLOCKED outcome is fully valid và có giá trị tương đương DONE.
