# Gateway Freeze, Event Loop Starvation & REASON vs EXEC Dispatch Contract

## 1. The 5-Stage Freeze Domino Effect (Incident Analysis 2026-09-25)

When subagents execute long blocking commands or tasks are poorly decomposed, the following domino chain freezes the entire Hermes gateway:

```text
[A] Coordinator assigns long-running blocking commands (119s, 180s terminal) to a subagent within a 600s budget.
    │
    ▼
[B] Subagent spends 80%+ of wall-clock time waiting on shell/ADB/test execution instead of LLM reasoning.
    Subagent hits the 600s child timeout, gets forcefully killed, and yields 0 useful results.
    │
    ▼
[C] Multiple subagents concurrently waiting on long synchronous calls exhaust the ThreadPoolExecutor/event loop threads.
    │
    ▼
[D] Gateway Event Loop becomes starved/blocked:
    - Cron scheduler log: "live adapter send to telegram:... timed out before the coroutine was dispatched".
    - Telegram webhook fails to return HTTP 200 within limits -> Telegram server reports "Read timeout expired" and halts delivery.
    - 0 LLM requests reach the local proxy/OmniRoute for 6-10 minutes.
    │
    ▼
[E] Children time out and exit -> Loop unblocks -> Telegram flushes queued messages in a sudden storm.
    100+ requests hit OmniRoute in seconds -> Account semaphore queues fill up -> 429 Semaphore Timeout cascade.
```

---

## 2. Key Decomposition Traps

| # | Trap | Mechanism of Failure | Mandatory Corrective Action |
|---|---|---|---|
| 1 | **Blocking commands in LLM worker** | Running `pytest`, large build, ADB loops, `sleep > 30s`, unbounded `logcat` synchronously inside subagent. | Run long-running tasks as **Background Jobs** (`terminal(background=True)` or cron). Worker only polls or inspects final log. |
| 2 | **Fat multi-discipline workers** | Combining code surgery, test execution, build, and live canary verification in one worker. | Split into sequential phases: (1) Code edit worker -> (2) Test/build job -> (3) Review/audit. |
| 3 | **Unbounded fan-out on shared resource** | Spawning multiple workers touching the same repository, same ADB device serial, or same LLM provider pool simultaneously. | Bound concurrency to $\le 3$ workers per batch. Enforce strict 1-worker-per-device/repo lock. |
| 4 | **Blind retry on timeout** | Retrying the exact same prompt after a 600s subagent timeout. | **CẤM retry prompt cũ**. Timeout = Structural Failure -> Decompose into a tighter exact patch contract (O(1) anchor) or execute background job. |

---

## 3. Mandatory Dispatch Classification: REASON vs EXEC

Before any `delegate_task` call, classify the subtask:

1. **`REASON` (Code surgery, AST inspection, log analysis, diff review)**:
   - Assigned to LLM worker subagent.
   - Individual tool commands must execute in $< 60\text{s}$ (preferably $< 10\text{s}$).
   - Total iteration budget $\le 8$ (hard ceiling 15).
2. **`EXEC` (Test suites, compilation, builds, batch phone farm operations, soak tests)**:
   - **FORBIDDEN** to run synchronously inside a foreground LLM worker.
   - Must be launched as a background process with PID/log file, or via standalone launcher.
   - LLM worker is only spawned *after* completion to inspect the exit code and final log slice.
3. **`PHONE` (ADB / ATX device automation)**:
   - Maximum 1 worker per physical device serial.
   - Individual ADB/UI commands must timeout in $< 30\text{s}$.
