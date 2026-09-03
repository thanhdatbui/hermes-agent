# Artifact-Backed State-Machine Audit

Use this for a recovery signature shared by multiple targets.

## Evidence record

For each target, capture:

- exact run directory and target/device identity;
- `report.json` status, failure code/signature, final state, and downstream side-effect flags;
- `checkpoint.json` recovery reservation, handler, lifecycle, attempt count, fingerprint/receipt state;
- execution-log lines covering classification, action, recapture, verifier, and terminal transition;
- every raw screenshot/UI XML/UI-capture artifact referenced by the checkpoint or log;
- hashes or deterministic pixel/parse metrics for binary/text artifacts.

Never treat a handoff, report summary, `VERIFIED_XML` capture transport result, or worker exit as proof that the target UI control was present. Those are metadata unless the raw artifact supports the claim.

## Safe-handler invariant

For a UI-changing recovery action, require all of the following before tapping:

1. exact surface classifier matches;
2. foreground/package guard passes;
3. fresh before artifact exists;
4. semantic control is present, clickable, labelled, and inside the bounded region;
5. one bounded action is acknowledged;
6. fresh after artifact and UI recapture prove the expected surface;
7. downstream work remains blocked until the final verifier succeeds.

If any input is missing or contradictory, the expected result is fail-closed (`FINAL_BLOCKED`, `MANUAL_REVIEW`, or the project’s equivalent), with no Post/workbook/cleanup success transition.

## Test decision rule

A regression test is justified only when it can go RED against current production using a faithful fixture or replay. If the available run has screenshots but no raw recaptured XML, do not manufacture XML from a summary. First run the existing focused tests and replay the available binary evidence through the production detector. If those already pass and the handler already fails closed, report `NEEDS_PROOF` and identify the exact missing artifact needed for a red-capable test.

## Minimal replay pattern

```text
for target in targets:
    read report + checkpoint + log
    enumerate referenced artifacts
    replay classifier/verifier on raw artifacts
    assert terminal status and no unsafe side effects
    record missing evidence separately from observed failure
```

Keep the report target-scoped and avoid live-device retry while establishing evidence. Use exact paths and command output so another session can reproduce the conclusion.
