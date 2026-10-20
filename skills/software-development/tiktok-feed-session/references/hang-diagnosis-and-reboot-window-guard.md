# Feed batch hang diagnosis and reboot-window guard

## Trigger
Use when a TikTok feed batch appears hung for more than ~30 minutes, especially near a scheduled reboot, or when a cron watchdog must keep running all day but avoid reboot windows.

## Evidence-first diagnosis
1. Capture current time and the parent runner PID/start time.
2. Inspect the runner's direct children: Python/workflow workers, device-command processes, and their status/CPU. A parent with CPU near 0% plus repeated `wait-for-device` children is evidence of I/O/device waiting, not proof of a code-worker stall.
3. Count completed machines from the exact run's `log.jsonl`; compute remaining machines from the declared target range.
4. Read the last event for stalled machines and inspect artifact/log modification times. Classify the blocker from actual evidence: `blocked-proxy-vpn`, device offline/USB disconnected, or `manual-needed`/detector miss.
5. For every confirmed `[MÁY N]`, run only `python D:/Taadaa/tools/inspect_machine.py <N>` before concluding. Do not use manual device input or advise cable pulling as a workaround.
6. Distinguish the deployed runtime from the source repo. A passing source test or worker self-report is not runtime proof; verify deployed copy/hash and effective scheduler configuration separately.

## Reporting contract
Report PID, start time, CPU/status, exact log/artifact path, completed/target count, last event, and the machine(s) blocking progress. Say explicitly whether the evidence points to the farm runner, device connectivity, proxy/VPN, or a code worker. Do not claim DONE/fixed without runtime verification.

## Reboot-window guard
If the user says “run all day but avoid reboot time,” preserve the all-day cron expression. Add a small explicit guard around each fixed reboot (for example, a 15-minute pre/post blackout), preserve existing feed/cache windows, run the focused pytest, inspect diff numstat, and verify the deployed runtime copy and effective schedule. Never pause or silently reschedule unrelated jobs.