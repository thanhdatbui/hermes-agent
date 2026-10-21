# Provider fallback, identity binding, and anti-paralysis

## Trigger
Use this reference when a UI/device job spans background execution, multiple accounts, or model/provider fallback.

## Durable lessons

1. **Exit code is not completion.** Keep these predicates separate: runner exited successfully; target artifact exists; visible account identity matches; postcondition is verified. `exit=0`, `verified=True`, workbook `OK`, or a success log line cannot replace fresh target-bound evidence.
2. **Bind every artifact.** Carry machine, serial, slot, username, run ID, and capture time through the runner and verifier. A later screenshot showing another account is contradictory evidence and must invalidate the claim; it is never a usable fallback.
3. **Provider fallback must preserve execution state.** If a quota or routing fallback changes the model/provider, retain the same incident, target, lease, artifact namespace, and next action. A fallback must not reset the task to a conversational answer or permit the turn to end without a terminal state.
4. **Only two terminal states are valid.** `VERIFIED_SUCCESS` requires fresh, readable, identity-matching post-action evidence. `MANUAL_REVIEW`/`FINAL_BLOCKED` requires a structured reason, attempted recovery rungs, and evidence paths. Narrative apology, explanation, or “unproven” without continuing the bounded recovery path is not a terminal state.
5. **Background completion is an event, not proof.** On wake-up, read the exact run artifact and reconcile it before replying. Reject stale, black, Home/Launcher, wrong-account, or missing captures. Continue the authorized recovery ladder; do not ask permission for already-authorized steps.
6. **Interruption needs resume state.** If a user message or provider switch interrupts an open incident, store it in a resume stack with target identity, current rung, next action, and a return condition. Do not let the session become idle while an incident remains open.

## Reporting format

Lead with the actual state in direct Vietnamese:

- `Trạng thái: VERIFIED_SUCCESS | MANUAL_REVIEW | FINAL_BLOCKED`
- `Đúng target:` machine / serial / slot / account
- `Bằng chứng:` exact artifact paths and fresh OCR/vision result
- `Sai lệch:` identity, timing, surface, or missing artifact
- `Bước tiếp theo:` one concrete bounded action

Never claim “đã xong” from a provider summary, model self-report, stale screenshot, or a mismatched account.
