# Offline Fail-Closed Harness Audit Patterns

Use this after a worker changes a deterministic scheduler, launcher, journal, verifier, or recovery harness. It is for offline fixtures/temp directories only; it must never be used to authorize device, account, workbook, cron, or production execution.

## Gate discipline

A green unit suite, compile pass, and `git diff --check` are preliminary evidence, not approval. Before commit, require all of:

1. Independent reviewer verdict from the reviewer’s final response: `APPROVED`.
2. Coordinator-run targeted/full tests and adversarial probes against the actual worktree.
3. Scope/allowlist review, untracked-file review, and whitespace check.
4. No active implementation worker or unresolved audit process for the same scope.

For a `REJECT`, auto-remediate only findings with a stable locator, deterministic branch/input/state, concrete impact, and an executed reproduction. Treat unsupported claims as `NEEDS_PROOF` rather than expanding scope.

## Root-cause adversarial matrix

| Surface | Mutation/probe | Required fail-closed behavior |
|---|---|---|
| State capture | Reader returns A then B across repeated reads | Capture each account’s feed/post state once; validate and reuse the immutable capture for digest, cadence, skips, IDs, and publication. |
| Manifest identity | Forge a self-consistent assignment ID, entry ID, or idempotency key | Canonical validation recomputes all derived identity from payload fields even without optional source context. |
| Skipped records | Insert recovery/manual/blocked/alert/post-only reason | Reject it; allow only an explicit scheduler/source/capacity skip allowlist and require complete account partitioning. |
| Journal | Append bare terminal event, unknown field, malformed/truncated/noncanonical JSONL | Reject before any launch/recovery action. Enforce closed per-event schema, fixed terminal flag, and legal transition sequence. |
| Dry run | `feed_then_post`, missing post handler, `execute=False` | Return preview before registry/lock/reservation/prepare/spawn and leave only a preview audit event. |
| Recovery classification | AUTH, OTP, CAPTCHA, payment, workbook, unknown, empty/unregistered handler | Sensitive cases are manual; missing handler is `NO_HANDLER_IMPLEMENTED`; neither may reserve or call a bridge. `UNKNOWN` has a closed handoff-only result shape. |
| Handoff evidence | Unrelated file, stale proof, symlink, wrong target/hash/signature | Reject. Require existing regular fresh proof plus canonical hash and bindings for manifest, entry, target, signature, ledger, and reference time. |
| Verifier | Duplicate/extra/missing target records, stale or symlink artifacts | Require the exact expected target set; reject ambiguity before deduplication. |
| Offline paths | Arbitrary state root, absent `--offline-root`, traversal, symlink, workbook/secret-like filename | Every CLI requires an explicit offline root; all paths remain contained and regular-file safe. |
| Logical time | UTC/fixed offset, malformed timestamp, 00:00–00:59, 01:00–05:59 | Require canonical local timestamps; map midnight to prior logical day and produce no due work during the closed early-morning interval. |

## Schema-first recovery design

Prefer one canonical source of truth for event schemas and transitions rather than scattered conditional checks:

- Define each event’s exact allowed/required fields and fixed terminal value.
- Define transition rules by `(entry_id, target, signature, attempt)`.
- Validate an entire persisted stream before acting on it.
- Reserve under the same lock that guards reconciliation; an unresolved reservation must block blind relaunch.
- Keep notifications separately idempotent and distinguish `reserved`, delivery failure, and `sent`.

When several findings share this structure, redesign the boundary/schema once and add regression probes; do not apply isolated assertion patches to each symptom.

## Auditor artifacts and bounded coordination

- Store a reviewer prompt, a final-result artifact, model/effort, scope, and verifier commands separately from raw tool transcripts.
- Raw CLI transcripts may echo prompts, source text, historical verdict words, and tool output. Never grep the whole transcript for `REJECT`/`APPROVED`; extract the final assistant response (for example with an output-last-message artifact) and read its first non-empty verdict line.
- Before starting a long worker or audit, capture a compact checkpoint: exact scope, current HEAD/status, known verdict/findings, completed verification commands, and remaining gates.
- Do not burn the coordination budget with blind repeated `wait`/`poll` calls. Use bounded status checks, inspect a result artifact or completion notification, then continue only when the process state materially changes.
- If execution is interrupted while a worker exists, report neither approval nor failure from process status alone. On resume, reconcile the process/result/worktree first, then run independent verification and a fresh audit if code changed.
