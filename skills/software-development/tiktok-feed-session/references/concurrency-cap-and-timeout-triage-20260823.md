# Concurrency cap and timeout triage

## Scope
Use when an operator wants more parallel feed machines so each account can finish the planned sessions, especially when XML/ATX work makes individual machines slow.

## Verified execution model
- Hermes `phase9-runner-tiktok-feed` fires every 15 minutes (`*/15`), not every 5 minutes.
- The runner reads the active manifest's due entries, groups them by physical `account_row`, and launches `scripts/run-feed-session.ps1` for each due row.
- The watcher schedule (`7,22,37,52`) is a reporting/recovery watcher, not a worker replenisher.
- The launcher passes `--max-workers`; `ThreadPoolExecutor` runs reserved machines concurrently up to that cap. Machines beyond the cap queue in the same batch; the system does not dynamically top up workers every five minutes.
- Current defaults observed in both launcher and consumer flow: `30`.

## Decision rule
Separate:
1. **Wave/queue pressure:** more workers can reduce the number of waves and improve the chance of completing all planned sessions in the window.
2. **Per-device latency:** slow ATX/ADB/XML capture, startup, popup probes, VPN/ViChanger, or recovery. More workers do not make one device faster and can increase shared pressure/timeouts.

Do not infer that timeout volume is caused by the worker cap until the logs distinguish queue delay from per-device timeout.

## Evidence-first checks
Before changing the cap:
- Inspect the actual scheduler cadence, active manifest due windows, launcher arguments, fallback default, and `ThreadPoolExecutor` cap.
- Read target-scoped `log.jsonl` and summarize timeout signatures separately: ATX unavailable, ADB transport, ViChanger GET_IP, max-duration deadline, capture artifact incomplete, popup/manual-needed, and code/logging errors.
- Use the production capture path for load testing: ATX session service, app launch + settle time + repeated XML/read/swipe loop. Do not substitute a one-call or `uiautomator dump` benchmark.
- Preserve device locks and do not run a live batch solely because static checks pass.

## Staged change guidance
Existing farm evidence recorded 20 as conservative, 30 as full-session-tested with no errors, and 40 as the point where light errors began. Therefore:
- Do not jump directly to 40+ based only on the desire to reduce waves.
- If the operator authorizes a cap increase, stage `30 -> 35 -> 40`, observe one complete operating window, and compare timeout/error rate, ATX availability, duration, and completed sessions.
- If changing defaults, update every real entry point that supplies the cap (PowerShell launcher default and Python fallback), then run compile/config checks and focused tests.
- Report the recommendation briefly: cadence, current cap, proposed cap, evidence, and blocker classification.

## Session-specific observation
A 2026-08-23 runtime scan showed failures were heterogeneous rather than a single worker-cap issue: ViChanger GET_IP timeouts, ATX/session availability, max-duration deadlines, incomplete profile capture artifacts, and a missing logger `result` keyword. This supports triage before simply raising concurrency.

Related procedure: `references/concurrency-cap-testing.md`.
