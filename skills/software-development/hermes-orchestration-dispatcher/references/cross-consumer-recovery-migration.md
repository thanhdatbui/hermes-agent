# Cross-consumer recovery migration reference

Use this reference when a shared recovery/control-plane feature is already shipped but the user asks to "deploy" it across consumer repositories.

## Evidence boundary

Separate these claims:

- **Core shipped:** shared state machine, lock retention, escalation interface, CLI, and tests exist.
- **Adapter migrated:** a consumer registers a strict handler/spec and escalation hook.
- **Runtime connected:** the adapter is called from the real consumer execution path, not only a scheduler/preflight gate.
- **Live proven:** device/run artifacts and verifier evidence exist. Static scans and offline tests are not live proof.

A core-only implementation is not fleet auto-recovery. Report each layer separately.

## Required matrix per consumer

Record, from safe source inspection:

| Field | Required evidence |
|---|---|
| Repo identity | absolute repo path, branch/HEAD, pre-existing dirty state |
| Core pin | exact requirements/pyproject line; distinguish recovery target from lock-rollout baseline |
| Failure taxonomy | real class/constant/function and source locator |
| Handler seam | strict registry/spec or `NOT_FOUND` |
| Runtime call-site | real caller; scheduler-only registration is not enough |
| Retry/cap | actual local budget and terminal state; never infer `FAILED_LOCKED` from `FINAL_BLOCKED` |
| Recapture/verifier | concrete function/artifact seam or `NEEDS_PROOF` |
| Device lease | acquire/finish/release/retention path or `NEEDS_PROOF` |
| Tests | existing focused tests plus new RED→GREEN cases |
| Migration status | `PENDING`, `NEEDS_PROOF`, or verified adapter/runtime-connected status |

Use `FACT`, `NOT_FOUND`, `NOT_INSPECTED`, and `NEEDS_PROOF` consistently. Never invent an insertion point when the runtime path is not located.

## Safe inspection boundary

Do not open or copy secrets, credentials, tokens, passwords, keys, auth/session material, workbooks/data tables, raw logs, mailbox data, or live-run artifacts. Do not run consumer scripts, ADB, devices, mailboxes, workbook writes, or `pm clear` for migration validation. If a consumer requires one of these to prove the seam, stop at `NEEDS_PROOF`.

## Recommended execution topology

1. Snapshot all affected worktrees and preserve unrelated dirty files.
2. Write and independently audit a plan before consumer edits.
3. Pilot one consumer with the strongest offline integration evidence.
4. Give that consumer one exclusive worker/worktree and exact allowlist.
5. Add contract tests before wiring the runtime path; prove no-hook, missing/incomplete handler, HARD_STOP, NON_RETRYABLE, generic exception, budget exhaustion, verifier failure, retained lock, restart/re-fire, redaction, and no implicit recovery.
6. Audit the material diff with the primary audit route, then commit only after `APPROVED`.
7. Repeat sequentially for the next consumer; do not patch all nine in parallel.
8. Package/pin a compatible core artifact only after the adapter contract is proven; ensure verification imports the intended worktree/artifact, not stale site-packages.
9. Finish with per-consumer focused suites, core suite, compile/diff checks, and an explicit list of consumers still pending.

## Pilot decision rule

Prefer the consumer with a real strict registry and a locatable runtime caller. If the registry is only in a scheduler/supervisor gate, the pilot must first prove or add the runtime connection. A missing runtime call-site is a discovery phase, not permission to guess.

## Integration cleanup pitfall

An untracked plan or generated artifact can block a clean merge. Preserve it byte-for-byte with hash and size, quarantine it outside both worktrees during guarded integration, restore it after merge/push, and verify the remote ref. Never delete or accidentally commit the artifact.

## Completion wording

Use wording such as:

> Core control-plane: shipped. Consumer adapters: N/9 migrated and runtime-connected. Remaining: list each consumer and why it is `PENDING` or `NEEDS_PROOF`. Live proof: none unless raw artifacts and verifier evidence exist.
