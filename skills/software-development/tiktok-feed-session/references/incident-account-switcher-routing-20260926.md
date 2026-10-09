# Incident learning: account-switcher routing (2026-09-26)

## Durable workflow corrections

- On a user request to fix until done, do not stop at `BLOCKED` merely because the live device has drifted to Launcher/Home. Separate: (1) code fix with diff + focused test, (2) target-scoped canary, (3) batch reopen decision. `UNPROVEN` limits the live-causality claim; it does not cancel a proven code fix.
- For `[MÁY N]`, run `python D:/Taadaa/tools/inspect_machine.py N`, read the newest targeted log/artifact, then dispatch a worker for code investigation. A worker timeout is transient: retry once with a narrower exact contract. Once the anchor is known, do not dispatch broad repository exploration.
- For large flows, the Coordinator should identify a unique anchor with targeted read/grep O(1), then give the worker an exact old→new patch contract and one focused test. If the worker times out after the anchor is known, retry the narrow contract or use the authorized escalation path when exact-diff requirements are met.
- Preserve classifier distinctions. If the classifier emits `manual-needed:account-switcher-missing-expected` or `manual-needed:login`, never replace it with a generic `account switcher blocked by manual-needed screen`; preserve the specific reason so M11/M66 and M40 remain separately routable.
- An explicit User instruction authorizes a shared/canonical cross-repo fix within the exact allowlist. Do not invent a consumer-only blocker contrary to that instruction. Keep scope lock, worker ownership, focused tests, diff evidence, and no blind live/destructive actions.

## Evidence pattern

Canonical account-switcher defects can be proven offline when a stable error path is found (for example, `ATX_SESSION_UNAVAILABLE` omitted from transient/recovery sets), even when the historical live incident remains unproven because only a later Launcher/Home inspection is available. Report those claims separately.
