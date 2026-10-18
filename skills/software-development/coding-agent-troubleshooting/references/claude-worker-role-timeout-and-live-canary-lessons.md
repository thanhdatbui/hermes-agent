# Claude Worker Dispatch, Timeout, and Live-Canary Lessons

Session-derived reference for Windows Taadaa farm coding-agent dispatch.

## Role/model contract

- `worker` is the implementation lane; it must use the approved Haiku alias (`haiku`) or the configured Haiku worker route. Do not pass an invented/version-specific model ID such as `claude-haiku-5-5` when the installed CLI catalog only recognizes aliases. Treat catalog warnings as a routing/configuration problem, not a reason to switch the worker to Sonnet.
- `worker` must reject any Sonnet model before starting a provider call. Sonnet is reserved for planner/reviewer work in this lane. The mechanical rejection must be tested with an exit code and a stable error marker such as `ROLE_MODEL_MISMATCH`.
- If Haiku fails or times out, fallback is the configured Agy fix route, never an automatic Sonnet upgrade. A fallback is a new hypothesis/route, not a blind replay of the same prompt.

## Timeout discipline

- The host rejects foreground terminal timeouts above 60 seconds. Use `background=True`, `notify_on_complete=True`, and a bounded outer timeout for non-trivial Claude/Agy work.
- The inner worker timeout and the outer process timeout are different values. A worker timeout can trigger an internal retry/fallback while the outer process is still running; do not call the task failed merely because the first timeout event appeared.
- After any worker timeout, inspect the target artifact/diff and run the focused test before deciding whether another worker call is needed. Worker exit code and self-report are not proof of edits or correctness.
- Never report “fixed/approved” while a worker or reviewer is still running. Dispatch, running, completed, and verified are separate states.

## Review and verification contract

For a code slice, use this order:

1. Snapshot the exact target and contract.
2. Dispatch the implementation lane with a bounded, self-contained prompt.
3. Inspect the actual diff after completion or timeout.
4. Run the focused offline test independently.
5. Ask the reviewer to inspect the actual file/diff and test result; bind the verdict to the current target state.
6. Only then report completion. A reviewer `APPROVED` is not a substitute for a real test or live evidence.

For the farm network gate, the focused acceptance set reached 40 offline tests. Important regression classes included secret-safe subprocess exceptions, workbook serial provenance, argparse rejection of unknown arguments, SSID-scoped authentication-failure detection, handshake grace before AUTH_FAIL, wlan0-aware L3 probing, TCP fallback when ICMP is blocked, and captive-portal ordering.

## Live-device canary discipline

- Perform a schedule/lock preflight before mutating a device. `force_preempt` is an explicit destructive operational choice; do not use it merely to bypass an active farm slot.
- A live result is authoritative only as returned by the gate and its raw device/AP evidence. Do not infer “L2 green” from a later-stage result. In the observed M7 case, the actual result was `L2_AUTH_FAIL`; Aruba reported an encrypted-message integrity failure, and the device had no wlan0 IP. The correct state was fail-closed at L2, not “connected but L3 broken.”
- Do not retry alternate Wi-Fi passwords after an authentication/MIC/integrity failure. Capture the failure, stop the lane, and fix the SSOT/AP/device-state cause through the approved recovery path.
- Keep live-device operations separate from offline code repair. A worker doing code edits must not silently turn a code task into an unbounded device loop.

## Common anti-patterns caught in this session

- Calling `terminal` foreground with `timeout=75` or `90` and then trying to explain the guard rejection. Mechanical rule: long CLI calls are background jobs.
- Passing `--model claude-sonnet-5-5` to a worker because the Haiku ID produced a catalog warning. Mechanical rule: reject role/model mismatch and route to alias or Agy.
- Treating a worker exit code of zero or a self-report as proof that the requested edit happened. Read the file, inspect the diff, and run the test.
- Claiming hardware success from a partial status. Report the exact gate status (`NOOP_HEALTHY`, `L2_AUTH_FAIL`, `L3_NO_IP`, `L4_PROXY_DOWN`, etc.) and the evidence that supports that stage.

This reference complements the class-level `coding-agent-troubleshooting` skill; keep provider-specific transcripts here rather than expanding the main skill with one-session filenames.
