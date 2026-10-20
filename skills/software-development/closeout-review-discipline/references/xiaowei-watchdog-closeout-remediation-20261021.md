# Long-lived Xiaowei watchdog closeout notes

## Trigger
Use this reference when a Windows watchdog tracks idle time, starts a sampler, and may terminate `xiaowei.exe`.

## Durable lessons
- A green focused suite is not proof of production safety: reviewers need evidence for sampler death/restart, malformed state, process replacement, lock contention, and final identity checks.
- `NEED_CONTEXT:<path>` is usually a payload-budget signal. Inspect the gate's truncation manifest and compact the test diff before adding more tests.
- Keep the implementation/test pair explicit. Worker self-reports are untrusted until `git diff --name-only`, diff size, and a fresh pytest run confirm them.
- A single-file worker lock cannot satisfy a two-file prompt. Dispatch production and test changes as separate scoped tasks or use a cohesive pair contract supported by the dispatcher.
- Preserve strict assertions while compacting: parameterize repeated state/threshold cases and centralize fake clocks, state writers, process-tree sequences, and subprocess result fixtures.
- For process-closing code, fail closed on unknown sampler health, stale heartbeat, invalid timestamps, missing `psutil`, PID reuse, and any identity change during the confirmation window.

## Evidence pattern
Record: focused pytest output, production diff bytes, total payload bytes, gate verdict/score, exact scope hash, and any backend or worker error. Never report `DONE`, `APPROVED`, commit, or push from a worker self-report alone.
