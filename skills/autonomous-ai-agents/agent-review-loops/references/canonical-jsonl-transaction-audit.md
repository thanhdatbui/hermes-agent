# Canonical JSONL Producer Transaction Audit

Use this checklist when an offline scheduler/runner appends canonical JSONL records while a sidecar enforces idempotency, and a watcher consumes the stream fail-closed. It does **not** authorize cron, device, account, workbook, gateway, or other live execution.

## Why append + sidecar needs a transaction

A superficially safe sequence can still violate the contract:

1. append report line;
2. flush/fsync report;
3. rewrite idempotency sidecar with `wb`;
4. flush/fsync sidecar.

A crash after step 2 leaves a durable report without state. A crash during step 3 can truncate all prior state. Blindly returning `written=False` when either artifact contains a partial match can then suppress a missing record; blindly raising forever destroys retry-idempotency even though the line was durably appended.

Treat report and sidecar as one recoverable state machine, not two independent files.

## Minimum durable protocol

The sidecar must bind every report position to all of:

- exact idempotency key `(manifest_sha256, entry_id, failure_signature)`;
- canonical record revision/hash;
- report line ordinal (or equivalent unambiguous ordering identity);
- transaction status such as `PENDING` or `COMMITTED`.

For a new key:

1. Validate the whole existing report and sidecar before mutation.
2. Atomically publish a `PENDING` intent: self-owned sibling temp file → write → flush/fsync → `os.replace`; reject symlink/nonregular/temp collisions.
3. Append exactly one canonical newline-terminated record and flush/fsync it.
4. Atomically replace state with the entry marked `COMMITTED`.

Direct in-place sidecar truncation is not sufficient merely because a later parser detects torn JSON. Detection is fail-closed, but atomic replacement preserves prior committed keys and gives deterministic reconciliation.

## Required reconciliation matrix

Each case needs a production-seam test and an independent temp-root probe:

| State | Report | Required result |
|---|---|---|
| no entry | no line | create pending → append → commit; `written=True` |
| `PENDING` exact key/revision/index | no line at bound index | append once → commit; `written=True` |
| `PENDING` exact key/revision/index | exact line present | do not append → commit; `written=False` |
| `COMMITTED` exact key/revision/index | exact line present | idempotent; `written=False` |
| `COMMITTED` entry | line absent, moved, or changed | fail closed; no mutation |
| no matching state entry | extra/orphan report line | fail closed unless a documented durable intent proves ownership |
| malformed/torn/noncanonical state or report | any | fail closed; no mutation |
| revision/index/order mismatch | any | fail closed; no mutation |

Do not implement reconciliation as “same `entry_id` + signature exists, therefore duplicate.” That loses the manifest dimension and can acknowledge the wrong line.

## Exact-key semantics across manifests

Idempotency is by the full triple, not the visible report subset. Two different `manifest_sha256` values with the same `entry_id` and `failure_signature` are distinct keys. If the approved report schema forbids emitting the manifest hash, two visible canonical lines may be byte-identical; the sidecar’s key + revision + ordinal binding must disambiguate them.

Test both directions:

- same triple twice → one line, second call `written=False`;
- different manifest hash with same entry/signature → two separately bound records, not a mismatch error.

## Schema and validator scoping

- Require the input failure mapping to have **exactly** the classification-field key set *before* merging it with `entry_id` and `target`. Otherwise an input can overwrite those arguments while state is keyed from different values.
- Enforce the parser-approved record key set exactly; no command, argv, environment, raw log/exception, workbook, credential, retry, recovery, release, restart, or action fields.
- Recursively reject sensitive keys and values in mappings and sequences.
- Terminal records must remain `FAILED_LOCKED` with `lock_safe=False`; their watcher path must return before journal reservation, bridge, retry, release, restart, or recovery code.
- Do not tighten a shared legacy target validator merely to satisfy the new producer. Preserve legacy parsing behavior and add a dedicated strict validator used only by the canonical producer/terminal-record path. Pin this with one legacy-accepted/new-terminal-rejected regression.

## Fault-injection TDD

Add tests before production edits and prove a real RED at the intended transaction branch. Useful hooks/faults:

- stop after pending-state publication;
- stop after report fsync but before committed-state publication;
- fail atomic replace;
- pre-create a torn sidecar;
- delete/reorder/change a committed line;
- add an orphan line;
- run concurrent processes, not only threads;
- inject an `entry_id`/`target` override into the failure mapping.

A syntax/import/fixture error, or a failure at an earlier schema gate, is not valid RED evidence. Capture the pre-edit hashes and top-level test-name set so a worker cannot silently delete/nest old tests.

## Audit and release gate

Before exact-byte audit, independently record HEAD/branch/status, allowlist, SHA-256, byte count, LF/CRLF/BOM, targeted/full suite, compile/static checks, and the reconciliation matrix outcomes. `MINOR_FIXES` or `REJECT` requires edit → fresh verification → fresh exact-byte audit. Commit only after `APPROVED`; any later byte change makes the verdict stale.
