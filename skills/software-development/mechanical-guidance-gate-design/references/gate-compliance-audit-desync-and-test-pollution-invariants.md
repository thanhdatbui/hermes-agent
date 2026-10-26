# Gate Compliance Audit Desync, Test Artifact Pollution, and Churn Metrics Invariants

## 1. Context & Root Cause
In automated agent environments, compliance watchdogs (such as `gate_compliance_watchdog.py`) periodically audit telemetry logs (`dispatch.jsonl`, `dispatch_audit.jsonl`, `guard_scan_audit.jsonl`, `console_block_audit.jsonl`) over rolling windows (e.g. 6h, 24h).
Two systemic flaws can corrupt audit conclusions:
1. **Pytest / Mock Pollution**: Unit test suites testing error handling (mocking `QUOTA`, `TIMEOUT`, `NEEDS_INPUT`) dump fake entries into shared production log files when not hermetically isolated. In practice, up to 75% of reported violations were test mock data.
2. **Timezone Desync (Naive Local vs UTC)**: Hooks logging via `datetime.now().isoformat()` emit naive timestamps in local time (UTC+7). Watchdogs operating on UTC that parse naive timestamps using `.replace(tzinfo=timezone.utc)` shift the 6h window by +7 hours, pulling in incidents from 13 hours prior.

## 2. Invariants for Compliance Auditing & Log Parsers

### A. Strict Test Artifact Exclusion
Every watchdog or telemetry parser scanning audit logs MUST filter out test and mock execution lines before gate evaluation:
- Ignore lines where `workdir` or `cwd` contains `pytest` or `tmp_path`.
- Ignore lines where target file is `target.py` or contains `pytest`.
- Maintain a dedicated helper `is_test_log_line(line: str) -> bool` that fails closed to exclude synthetic test runs.

### B. Timezone Normalization for Naive Log Files
Audit files emitted by Python hooks often lack timezone offsets:
- Files with naive local timestamps (e.g. `dispatch_audit.jsonl`, `console_block_audit.jsonl`) MUST be identified (`LOCAL_NAIVE_LOGS`).
- When parsing timestamps without `tzinfo`, if the file is in `LOCAL_NAIVE_LOGS`, localize it to the host timezone before converting to UTC:
  ```python
  if dt.tzinfo is None:
      if path_name in LOCAL_NAIVE_LOGS:
          dt = dt.astimezone().astimezone(timezone.utc)
      else:
          dt = dt.replace(tzinfo=timezone.utc)
  ```

### C. Tri-State Gate Classification (Eliminating False Alarm Fatigue)
A gate interception is a safety fence, not necessarily a failure:
1. **PASS**: Operation complied with policy from the first call.
2. **REWIRED / SELF_HEALED**:
   - **0-Turn Auto-Rewire**: The hook intercepted and automatically mutated the args (`action: "rewrite"`, auto-clamp budget). Zero turn overhead.
   - **1-Turn Guided Recovery**: The agent was blocked, read the `guidance` / `required_action`, and successfully pivoted on the very next attempt ($\le 1$ turn).
   - *Status*: Marked as `REWIRED` (🔄), NOT red `FAIL`.
3. **FAIL (Looping / Deadlock)**:
   - The agent was blocked $\ge 3$ consecutive times on the same rule/route without making progress.
   - Unremediated closeout rejections or system errors.

### D. Churn Metric for Guidance vs Auto-Rewire Prioritization
Measure average churn (number of turns spent per block event) to direct engineering effort:
- **Churn $\le 1.0$**: Text guidance is clear and actionable; agent recovers immediately.
- **Churn $> 2.5$**: Agent is confused by prompt nuances or repeated refusals (e.g. `subagent_edit_blocked` where agent repeatedly retried `delegate_task`). Text guidance is insufficient; mandatory upgrade to mechanical **Auto-Rewire** (rewriting the tool call directly to `dispatch_worker.py`).
