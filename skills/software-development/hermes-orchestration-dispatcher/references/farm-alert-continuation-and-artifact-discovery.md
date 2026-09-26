# Farm Alert Continuation & Artifact Discovery

## Why this reference exists

A Farm Alert is an execution request, not a request for a one-shot diagnosis. The common failure mode is to inspect one or two recent run directories, fail to find the target serial, and prematurely report `BLOCKED/UNPROVEN` even though the runner emits historical artifacts elsewhere in the canonical repo.

## Bounded procedure

1. Resolve the exact repo from the alert's `Script:` field.
2. Run the mandatory live inspection for the named machine, but treat it as current evidence only.
3. Identify the runner's canonical artifact root and its run-index shape. Prefer known direct roots, manifests, and summaries; do not broad-scan the disk or invent recursive searches.
4. Inspect the newest relevant run roots first. If the serial is absent, continue with bounded historical lookup by exact serial, machine ID, account, and alert timestamp. Do not conclude “no artifact” from a hand-picked list of runs.
5. For each candidate, verify the identity tuple: `run_id + device_serial + machine + account + start/end time + artifact root`.
6. Open the exact `summary.txt`, `run_manifest.json`, `log.jsonl`, matching `ui.xml`, and matching screenshot for the same attempt. A path listed in a manifest is not proof until the file is opened and exists.
7. Classify the result:
   - `CONFIRMED`: exact target identity and artifact support the alert.
   - `EXCLUDED`: artifact belongs to another device/account/run or disproves the claimed state.
   - `UNPROVEN`: the expected artifact class is missing, stale, corrupt, or identity is ambiguous.
8. Continue the A→Z loop: classify transient vs structural vs scope/business; dispatch the narrow worker/code-fix lane when a reusable defect is plausible; independently verify diff and focused test; run only the exact-target canary when authorized.
9. A terminal `BLOCKED` report must include the bounded discovery scope, exact paths checked, identity mismatch/missing-artifact reason, attempted next action, and a machine-readable stop predicate. “Need more evidence” alone is not a valid stop.

## Important distinctions

- A current `LauncherActivity`/sleep result does not erase a historical login-screen artifact, and a historical artifact does not prove the current device state.
- A login-screen reason on one serial must never be assigned to another serial merely because both belong to the same batch.
- A run with `feed not confirmed` is not equivalent to `login/account screen detected`; preserve the runner's exact reason.
- A Claude CLI timeout is an unverified audit, not `APPROVED` and not evidence that the design is absent.
- If an active rule already specifies `ALERT → EVIDENCE → CLASSIFY → WORKER → VERIFY → CANARY → DONE/BLOCKED`, report `DESIGN_PRESENT`; investigate the enforcement gap instead of designing a second policy.

## Incident lesson

In the September 2026 Kibe Farm incident, serial `ce0418244d10342502` was absent from three initially inspected recent runs but existed in the historical run `.ai-runs/20260922-001530`. The direct login-screen artifact found under `.ai-runs/20260902-074031` belonged to serial `988627464e374e3234`, not M40. The correct conclusion required both facts: M40 had historical artifacts, while the specific login claim for M40 remained unproven until the exact batch run was identified.
