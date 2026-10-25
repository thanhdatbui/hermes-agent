# Exception-Driven Alerting, 24H Heartbeat & Pre-Tool Auto-Rewrite

## 1. Pre-Tool Auto-Rewrite (In-Place Argument Mutation)
### Problem:
Passive vetoes (`action: block`) on trivial configuration errors (e.g. missing `timeout` in terminal calls or reading oversized log files > 10MB) cause LLMs (especially Gemini/Flash) to spend 8–9 turns searching for evasions (`grep -r`, `os.walk`, bash workarounds), generating thousands of unnecessary block events.

### Mechanism:
1. **Engine Level Support (`shell_hooks.py` & `plugins.py`):**
   - Hook parses `{"action": "rewrite", "updated_args": {...}}`.
   - Plugin directive mutates `tool_input_kwargs` in-place (`args.update(updated)`).
   - Tool executes immediately in the current turn without raising an exception to the model.
2. **Applied Rules:**
   - `guard_broad_grep.py`: Injects `timeout=60` (or `360s` for coordinator-dispatch allowlist) when omitted.
   - `guard_read_file_size.py`: Injects `offset = total_lines - 200, limit = 200` on files > 10MB when unbounded.

---

## 2. Exception-Driven Watchdog Architecture (Silent on Nominal, Loud on Anomaly)
### Problem:
Watchdogs sending repetitive "Everything OK" reports spam user communication channels (Telegram). However, purely silent watchdogs risk "False-Negative Masking" — when an unexpected failure, unhandled crash, or DB lock silently suppresses reports, leading operators to assume systems are healthy.

### Core Invariants:
1. **Three-State Health Model:** `NOMINAL | ANOMALY | UNKNOWN`.
   - `NOMINAL` must be positively proven (data source readable, freshness intact, metrics within thresholds).
   - Any unhandled exception, missing data source, or failed evaluation automatically resolves to `UNKNOWN -> ANOMALY`.
2. **Fail-Closed Timestamp Guard:**
   - If a log entry contains block/deny markers (`action: block`, `DENY`, `REJECTED`, `QUARANTINE`) but timestamp parsing fails, the entry MUST NOT be dropped if the file's `st_mtime` falls within the observation window.
3. **Catch-All Unclassified Bucket:**
   - Any block event that does not match known gate patterns is captured into `[Unclassified]`, forcing an `ANOMALY` alert so new rules never fail silently.
4. **24H Heartbeat Pulse (Dead Man's Switch):**
   - At 00:00 UTC (07:00 VN), exactly one summary heartbeat is emitted even if 0 anomalies occurred.
   - An absence of the 07:00 VN pulse alerts the operator that the watchdog or gateway itself is down.
   - All other intervals throughout the day stay 100% silent when nominal (`no_agent: true` with empty stdout).

---

## 3. Standardized Implementation (`cron_alert_core.py`)
All farm cron watchdogs integrate via a single O(1) context manager:

```python
from cron_alert_core import CronRun

with CronRun("my_watchdog", force_report="--force" in sys.argv) as run:
    # 1. Require data source (auto-fails closed if missing or empty without allow_empty)
    data = run.require_source(load_data, name="accounts_db", allow_empty=False)

    # 2. Check metrics
    run.check("stale_accounts", len(stale), ok=lambda v: v == 0, severity="P1")

    # 3. Attach report text (only printed if anomalies exist or force_report is set)
    run.set_report(formatted_msg)
```
- **State Registry:** Emits `runtime/cron_health/<script_name>.json`.
- **Aggregator:** `cron_heartbeat.py` evaluates all state files independently at 00:00 UTC.
