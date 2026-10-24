# Offline Fix vs Live Canary Gate

## Reusable lesson

A farm incident can have a green mocked regression test while the live canary remains unexecuted. These are separate verification claims and must never be merged.

## Evidence sequence

1. Normalize the alert machine label to its numeric ID and run the canonical inspector once.
2. Record serial, model, power/screen state, and current focus. Launcher or Sleep is only a current-surface observation; it does not prove the historical blocker.
3. Read the exact run artifact (`log.jsonl`/`summary.txt`) and inspect the named code seam before patching.
4. Keep the batch locked. Reproduce the signature with mocked XML/ADB seams and add one focused regression test.
5. Verify the exact diff scope (`git diff --numstat`, `git diff --check`) and run the focused test, then the target test file if time permits.
6. Run the repository's official single-machine canary exactly once with the approved machine/row parameters. Do not substitute a direct ADB action or an unrelated runner.
7. PASS requires fresh machine-scoped artifacts: manifest, summary, log, matching UI XML, and matching screenshot. Exit code or worker prose alone is insufficient.
8. If the official runner is blocked by a policy/guard, report `LIVE_CANARY_BLOCKED` with the literal guard output, keep the fleet closed, and do not report DONE or reopen the batch.

## Patch discipline

Use an exact function/file contract, preserve selectors and fail-closed behavior, and keep offline tests deterministic. A transient UI timing fix should be bounded (for example, one additional recapture) rather than an unbounded polling loop.
