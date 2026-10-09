# Model-routing forensics and bounded remediation

Use this reference when a Hermes/OmniRoute session becomes slow, repeatedly remediates, or appears to switch from Gemini to Luna.

## What counts as proof

- `config.yaml` fallback entries prove only that a fallback route is configured.
- A worker self-report or parent model name does not prove the model that served a request.
- For OmniRoute call logs, inspect per-request `summary` fields:
  - `model` — resolved/served model;
  - `requestedModel` — model requested by the client/combo;
  - `provider`, `comboName`, `comboStepId` — route and combo step;
  - `status`, `duration`, `account`, `connectionId`;
  - top-level `error` when the request failed.

A claim such as “Gemini quota was exhausted and Luna took over” is proven only when the records show the Gemini request failed for an explicit quota/rate-limit reason and a subsequent request resolved to Luna. `429`, `You've hit your limit`, and provider quota messages support quota exhaustion. `403`, `5xx`, timeout, `Request aborted`, `all targets skipped`, and connection errors are separate transport/provider failure classes until corroborated.

## Diagnose the loop separately from model identity

The common failure chain is:

```text
provider failure or quota event
→ fallback model serves the next request
→ coordinator sees reviewer rejection
→ remediation worker edits again
→ diff/scope grows
→ reviewer payload gets heavier or falls back again
```

This does not prove the fallback model caused the scope growth. Compare, per remediation iteration:

- task lineage/parent ID;
- resolved model;
- changed files and `git diff --numstat`;
- raw diff bytes;
- reviewer verdict/score and concrete findings;
- worker calls and wall time.

## Bounded policy

Do not choose between “no cap” and a blind universal two-round cap. Use separate controls:

1. **Worker contract cap:** one concern, one component, explicit allowlist, unique anchor, focused test, and a small diff ceiling.
2. **Remediation budget:** a finite number of evidence-backed remediation rounds for the current candidate; each round must close a concrete finding and change the candidate bytes or frozen contract.
3. **Stop/reconcile state:** when the budget is exhausted, findings repeat without byte change, scope ownership is ambiguous, or the candidate is polluted by unrelated dirty work, stop spawning workers and report the exact evidence. Do not call this a model failure without model telemetry.
4. **Transient retry budget:** retry provider/network failures separately; do not spend a remediation round or change candidate code for a transient transport error.

A diff-size threshold is a scope-control heuristic, not proof that the reviewer cannot handle larger changes. Reject or split an oversized candidate before review when it violates the task contract; do not blindly impose a 24 KB universal gate that blocks legitimate changes.

## Non-code closeout

Tasks that produce no code candidate (for example, a question, log inspection, workbook-only edit, or operational restart) should not be sent through a code closeout reviewer. Mark the closeout as not applicable only after reconstructing the task ledger and confirming there is no in-scope code/test artifact.

## Safe cleanup

A dirty gate file or mixed worktree is evidence of scope contamination, not permission to revert it. Preserve foreign/unowned changes; reconcile ownership and inspect the exact diff before any restore/revert action.
