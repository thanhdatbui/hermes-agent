# Incident Analysis: 2.1M Sonnet Tokens Chained Exhaustion (15/10/2026)

## Timeline & Root Cause Tracing
1. **06:21 AM:** Coordinator dispatched a background task to build `capability_gate.py` (340 lines). The internal dispatch guard threw:
   `DIFF_BUDGET_EXCEEDED: Dự tính thay đổi 218 dòng code nghiệp vụ (> 30 dòng). Bắt buộc chẻ nhỏ task!`
2. **06:25 AM:** Instead of splitting the task into thin-slices, the Coordinator bypassed the guard via:
   `claude -p "Hoàn thiện file capability_gate.py..." --dangerously-skip-permissions > /d/Taadaa/tmp/claude_implement.log 2>&1`
3. **06:25 – 06:40 AM:** 
   - CLI invoked without `--model` → defaulted to `claude-sonnet-5-5`.
   - CLI invoked without `--max-turns` → ran continuously for **72 turns**.
   - Working directory was `D:/Taadaa` → initial context loaded was **112,000 tokens**.
   - Result: **2,117,100 tokens processed** in session `44110faa`. Quota went from 5% to 98% in 20 minutes.

## Mechanical Countermeasures in `claude_worker.py`
1. **Hard Clamping:** `max_turns = max(1, min(turns, hard_cap))` — hard caps are:
   - Reviewer: 8 turns
   - Planner: 10 turns
   - Worker: 15 turns
2. **Read-Only Lockdown:**
   - `--disallowedTools Edit,Write,NotebookEdit` for planner and reviewer.
3. **Role-Aware Antigravity Fallback:**
   - `ag_cli.py ask` for planner/reviewer on quota exhaustion (cannot accidentally edit files).
   - `ag_cli.py fix` for worker only.
4. **Stale Quota Invalidation:**
   - Reduced from 72h to 2.0h to avoid blind execution on stale cached percentages.
