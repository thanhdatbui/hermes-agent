# Farm Alert Continuation & Artifact Discovery

## Incident lesson

A farm alert may name a machine and a failure phrase, while the first few recent run directories contain other devices or only successful sessions. That is not evidence that the target has no artifact. In one incident, the coordinator searched three recent runs, missed the target serial, and incorrectly reported “no M40 log”; a bounded historical lookup later found the exact serial in an older `run_manifest.json`, `log.jsonl`, `summary.txt`, and screenshot/XML artifacts.

## Required identity tuple

Before using an artifact as proof, bind:

- `run_id`
- machine number
- device serial
- account
- run timestamp
- exact artifact root
- attempt path for the matching `screen.png` and `ui.xml`

A historical artifact proves historical state only. It does not prove association with the current alert unless the run timestamp/manifest matches the alert batch.

## Bounded discovery sequence

1. Resolve the canonical machine→serial mapping.
2. Inspect the mandatory live machine state using the approved machine-scoped command.
3. Read the current/batch manifest and exact run summary/log where available.
4. Inspect bounded recent run roots.
5. If the serial is absent, perform bounded historical lookup by exact serial, machine, account, and timestamp. Do not broad-scan the drive and do not infer absence from a hand-picked recent subset.
6. Open the exact matching `summary.txt`/`run_manifest.json`/`log.jsonl`, then the matching attempt `ui.xml` and `screen.png`.
7. Classify each candidate `CONFIRMED`, `EXCLUDED`, or `UNPROVEN`.

## Failure-signature discipline

Do not transfer a reason between devices. For example:

- `feed not confirmed` is not `login/account screen detected`.
- A login detector result for serial A cannot prove login loss on serial B.
- Current Launcher/Sleep state and historical TikTok artifacts answer different questions; preserve both with timestamps.

## Continuation gate

`UNPROVEN` is not automatically terminal. Continue to reusable-code assessment, scoped worker dispatch, focused offline verification, and target-scoped canary when the target is resolved. A valid terminal report must include:

- exact paths checked;
- identity tuple and missing-artifact reason;
- classification and concrete failure signature;
- attempted next action;
- machine-readable stop predicate (`DONE`, `BLOCKED_<stage>`, `HARD_STOP`, or `TARGET_RESOLUTION_UNPROVEN`).

“Need more evidence” without the bounded discovery work and a stop predicate is not a valid closeout.

## Policy-design lesson

Before designing new orchestration, inspect existing rules for the canonical sequence. If the design is present, report `DESIGN_PRESENT` or `DESIGN_PARTIAL` and focus on runtime enforcement. Treat a referenced workflow file as implemented only after verifying its path. A Claude CLI timeout is an unverified audit, never an approval and never proof that the design is absent.
