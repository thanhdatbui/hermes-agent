# Gate Compliance Watchdog: Churn Metrics, Test Isolation & Timezone Alignment

## 1. Core Principles
When auditing gate compliance and mechanical enforcement over rolling windows:

### A. Test / Mock Data Isolation (Anti-False-Positive Invariant)
Unit tests and mock harnesses (e.g. `pytest`, `test_dispatch_worker.py`) running negative scenarios dump simulated failure events (`QUOTA`, `TIMEOUT`, `NEEDS_INPUT`) directly into shared logs (`dispatch.jsonl`, `dispatch_audit.jsonl`).
- **Filter Invariant:** Any line containing `pytest-of-`, `target.py`, `tmp_path`, or `_test_` in `workdir`, `cwd`, `file`, or `target` MUST be stripped before calculating gate pass/fail rates.
- Without this filter, up to 75% of reported gate violations are test noise.

### B. Timezone Naive vs Aware Alignment
- Production daemons and hook scripts running on Windows often log local naive timestamps via `datetime.now().isoformat()` (UTC+7).
- Rolling window audit monitors (`--hours 6`) comparing against UTC cutoff (`datetime.now(timezone.utc)`) MUST identify local-naive sources (`dispatch_audit.jsonl`, `console_block_audit.jsonl`) and convert them to UTC aware datetimes via `.astimezone().astimezone(timezone.utc)`.
- Treating naive local time as UTC causes a 7-hour forward desync, auditing the wrong time window.

### C. Tri-State Compliance Classification: Pass vs Rewired vs Fail
Never penalize a gate as `FAIL` when an interception successfully recovers:
1. **PASS:** Clean execution conforming to contract from turn 1.
2. **REWIRED / SELF-HEALED (0–1 Turn Overhead):**
   - **0-turn Auto-Rewire:** Hook automatically rewrites or clamps arguments (`action: rewrite` / auto-clamp). 0 turns wasted.
   - **1-turn Guided Recovery:** Intercepted once, agent reads actionable guidance (`required_action`), and executes cleanly on the very next step.
   - Status: Marked as `REWIRED` / `GUIDED_PASS`, NOT `FAIL`.
3. **FAIL (Churn Friction / Deadlock):**
   - Intercepted $\ge 2$ consecutive turns on the same rule without recovery, or total loop stall.
   - Requires red status and alerts operator that guidance is insufficient and needs Auto-Rewire promotion.

### D. Sol Dispatch Ladder Configuration
- Sol Worker (`gpt-web-sol` via OmniRoute `:20129`) default: `12 turns`, `480s` timeout floor.
- Prevents premature turn-cap timeouts during multi-hunk patching workflows.
