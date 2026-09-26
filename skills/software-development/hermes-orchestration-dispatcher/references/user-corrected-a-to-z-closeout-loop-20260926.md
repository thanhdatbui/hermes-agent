# User-corrected A→Z closeout loop (2026-09-26)

## Lessons

- “Làm từ A–Z”, “sửa đi”, “làm đi”, and “chốt phiên” are execution commands, not requests for a progress update. Continue until `DONE` or `BLOCKED` with evidence; never stop at `IN PROGRESS` while worker, test, review, or closeout steps remain.
- For code/workflow changes, call Sol planning first and obtain the exact patch contract before dispatching an implementation worker. A premature worker result is untrusted until reconciled.
- Bind every worker and test to the exact repository. A result from another repo is invalid evidence.
- On closeout failure, classify the failure and continue the repair→focused test→closeout loop. Do not claim closeout from isolated tests alone.
- Distinguish worker timeout, deterministic fixture/contract failure, and closeout hard-cap timeout. Identify the exact failing/hanging test with bounded verbose execution before patching.
- When a deterministic test fails, compare the live production default/contract with the fixture. Prefer a minimal stale-test/fixture repair over changing production solely to satisfy old assertions.
- For frustrated users, report verdict and evidence briefly; avoid repeated orchestration theory.

## Canonical evidence pattern

1. Record exact repo, dirty paths, and closeout command.
2. Run the exact focused node that fails; capture real output.
3. Use Sol for a bounded patch contract when code/workflow mutation is needed.
4. Dispatch a narrowly scoped worker; verify its files independently.
5. Run the focused node, relevant focused group, then closeout gate again.
6. Only `APPROVED` with the required score permits session closure.
