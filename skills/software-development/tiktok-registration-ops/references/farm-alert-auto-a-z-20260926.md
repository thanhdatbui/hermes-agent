# Farm Alert Auto A–Z

## Purpose
A farm alert is an execution trigger, not a diagnosis-only request. Continue automatically until `DONE` or evidence-backed `BLOCKED`.

## State machine
`ALERT → EVIDENCE → CLASSIFY → FIX WORKER → VERIFY → CANARY → DONE/BLOCKED`

## Required execution
1. Read the exact current run log, then matching XML and screenshot artifacts.
2. Resolve the correct host/cluster, machine, serial, workbook, lock, and canonical runner. If mapping is wrong, pivot and verify again; never guess another machine.
3. Classify each fingerprint as transient, structural, infrastructure, business/ownership, or mixed.
4. For structural faults, dispatch an exact patch contract to a worker. Independently verify allowlisted diff, focused offline test, syntax, and diff hygiene.
5. Retry transient transport/API failures with backoff, at most two times.
6. On repeated structural failure, redispatch with a materially narrower scope and different hypothesis. If the exact diff is known and emergency-surgery budget/invariants allow, apply the bounded surgery; verify it like any other patch.
7. After patch verification, run a canonical one-machine canary. Read fresh evidence; if a new fingerprint appears, classify and fix it rather than stopping at the first canary failure. Expand to a bounded group only after the canary passes.

## Ask-user gates only
Do not ask for normal in-budget work. Ask only for: missing credentials; business/ownership/account decisions; irreversible or paid actions; or a blocker remaining after retry, redispatch, surgery, and host/mapping/runner pivot are exhausted. Before asking, list evidence, attempts, branches tried, blocker, recommendation, and safe default.

## Blocked report contract
`BLOCKED` is valid only after escalation and evidence. Report: incident ID, target/host/serial, signature, classification, attempts/ledger, artifact paths, files/diff, focused test, canary result, lock state, and one concrete next owner action. Never report diagnosis alone as completion.

## Safety invariants
Preserve FARM-ASSET ownership, OTP/credentials, lock retention, visual evidence, no destructive account actions, no manual ADB firefighting, no broad filesystem scans, and closeout/reviewer gates. Safety gates block destructive or unauthorized actions; they do not block authorized triage, code fix, offline verification, or bounded canary.

## Incident lesson
For TikTok REG, validate every new fingerprint exposed by a canary. In the 2026-09-26 incident, the first patch correctly classified `Xác minh email` as `registered_otp`, but the next canary exposed a different `Chọn một tùy chọn đăng nhập` bottom sheet. Treat that as a new structural detector case, not as proof that the first patch failed.