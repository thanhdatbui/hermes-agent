# Probe Fidelity — Forge/Re-hash Verification Probes Must Mirror Production Derivation

When ad-hoc verification re-forges hash-bound identity (`assignment_id`, `entry_id`,
`block_id`, manifest digests), the probe answers "does production derivation still
accept/reject this shape?" — so every probe input must be derived EXACTLY as production
does. Two incidents from one session (commit fc61be9, hermes_cron manifest validation,
`D:\Taadaa\tiktok-luot nuoi acc`) where the PROBE — not the product — was wrong, and the
canonical suite was the tie-breaker that proved it.

## Incident 1: fixture key-set typo → silently EMPTY pick → probe tests the legacy path

Feed-state fixture had an extra key `"unreserved_reservation": False` (typo for the real
`"unresolved_reservation"`). `_validate_feed_state` requires an EXACT key set, so every
account's state became invalid → picker skipped the whole lane (`INVALID_FEED_STATE` +
`UNSCHEDULABLE_CAPACITY`) → payload had **zero blocks**.

Symptoms:
- Probe 1 "passed" vacuously (an empty `blocks` list returns early in the legacy branch of
  `_validate_block_structure` — the hardened block path was never exercised).
- Probe 2 crashed `IndexError: list index out of range` on `payload["blocks"][0]`.

Rule: **assert the preconditions your probe depends on** (`assert len(payload["blocks"]) == 3`)
BEFORE probing, so a silently-empty fixture fails fast at the seam instead of faking a pass.

## Incident 2: re-derived `assignment_id` missing skipped accounts

Source-less forge probe (machine 999 rehash, mirroring the passing r10 test) recomputed
`assignment_id` with `account_ids = sorted(entry accounts)`. Production
`validate_manifest` derives `account_ids` as the MANIFEST account-coverage set =
entry accounts ∪ skipped account ids (when `source is None`, `expected_ids` is None →
`assignment_accounts = sorted(accounts)` where `accounts` includes skipped). With a
6-account fixture (3 entries + 3 skipped), the probe's stale assignment failed with
`MANIFEST_IDENTITY_MISMATCH` while the canonical suite's identical-shape r10 test PASSED —
proving the probe derivation was wrong, not the product.

Rule: when re-deriving identity, list every input of the production derivation function and
replicate each — including DERIVED sets (coverage sets that fold in skipped/extra records),
`state_snapshot_digest` normalized `"0"*64 → None`, `generation` passthrough, and which
source variant (`source=None` vs real SourceConfig) changes what is bound.

## Tie-breaker rule (avoid "fixing" production for a probe bug)

If an ad-hoc probe fails but the canonical suite contains a PASSING test with the same
attack shape, the probe is wrong. Diff the probe's derivation against the production
derivation line by line; fix the probe; re-run. Never touch production code based on a
probe that contradicts the suite. Report probe fixes as probe bugs in the final summary —
do not fold them into product evidence.

## Incident 3: one shared temp root across probes → load-time validation mismatch

Verification probe ran probes 1–3 (fleet source, day 2026-08-10) and probe 4
(p1_r2 make_snapshot, a DIFFERENT source config, same day) against the SAME
`TemporaryDirectory` root. The picker loads the existing active manifest for the day and
validates it against ITS source; probe 4's picker loaded the fleet manifest written by
probes 1–3 → `MANIFEST_IDENTITY_MISMATCH` at load, before the forge was even built. The
canonical R10 test passes because each test gets a fresh root. Rule (already in SKILL.md,
this is a second failure mode): **one fresh temp state root PER probe** — roots are not
shareable across source configs, not just across journal/state replays.

## Incident 4: reject-assertion used the WRONG SourceConfig → wrong reason code

Probe forged a manifest from p1_r2's `SOURCE` (accounts acct-a/b/c) but asserted rejection
against `fleet_source()` (accounts acct-1..6, different `source_revision`). The revision
gate (`payload["source_revision"] != source.source_revision` →
MANIFEST_IDENTITY_MISMATCH) fired BEFORE the intended machine-resources gate, so the probe
reported the wrong code. The manifest must be validated against the source it was BUILT
from (or a source that shares its revision); only then does the intended gate (machine-999
not in source → MAPPING_CONFLICT) fire. Rule: when asserting which gate rejects a forge,
match the probe's SourceConfig to the forge's own source family.

## Checklist for writing forge/rehash probes

1. Read the production derivation function completely; enumerate every hash input.
2. Mirror derived sets exactly (coverage sets, sorted() order, None-normalization).
3. Verify fixture dicts satisfy the parser's EXACT key set (extra key = invalid; missing
   key = invalid; both silently change behavior).
4. Assert seam preconditions up front (`len(blocks) == 3`, `len(entries) == 6`) so empty
   picks can't fake a pass.
5. On unexpected probe failure: canonical suite is the arbiter; fix the probe first.
6. Keep probes OUTSIDE the repo under the OS temp dir (`hermes-verify-` prefix), run with
   explicit `sys.path.insert(0, repo)`, and delete after — see `windows-probe-execution.md`.
7. One fresh temp state root PER probe — never share a root across probes that use
   different source configs (a picker load validates the existing manifest against ITS
   source and can reject a foreign probe's manifest at load).
8. When asserting the reject-reason of a forge, validate against the SourceConfig the
   manifest was BUILT from (same `source_revision` family); a mismatched source fires the
   revision gate first and reports a different reason code than the gate under test.
9. Assert the EXACT reason code and probe which gate fires on old code — a bare
   `pytest.raises(ValueError)` is branch-deaf (any earlier gate passing the same error
   makes the test green while the branch under audit never executes).
10. When the literal attack shape can't reach its branch (canonical-slot binding,
    per-machine block counts, source uniqueness), find the OBSERVABLE difference:
    valid-payload accept/reject or a reason-code delta; derive multi-machine payloads by
    cloning + full re-hash if the picker can't emit them; use staged fix states as RED
    evidence to isolate each bug.

## Incident 5 (commit 6c47826): branch-deaf suite tests — "adversarial" tests that never reach the branch

Two pre-existing adversarial tests were PASSING but branch-deaf:
- `test_validation_rejects_inter_block_gap_too_small`: moved block-2 entry slots to 12:00 →
  caught by the session_slots binding gate (MANIFEST_IDENTITY_MISMATCH); the inter-block
  gap check never executed. Entry slots are hard-bound to canonical anchors
  (`session_slots == build_block_sessions(...)` AND `session_slots == entry slots`), so slot
  tampering can NEVER reach the gap branch with a tampered slot.
- `test_validation_rejects_duplicate_account_across_blocks`: mutated block account without
  syncing entry accounts → rejected by source binding / entry-level account_blocks, not by
  the block-structure `account_blocks_idx` under audit.

Rule: **assert the exact reason code** (`excinfo.value.args[0] == ReasonCode.X.value`) and
empirically probe which gate fires on OLD code before trusting a test to cover a branch. A
bare `pytest.raises(ValueError)` is branch-deaf — the suite can be 100% green while the
check under audit never executes.

## Observable-difference principle: when the literal attack shape can't reach the branch

The audit's literal shapes (move block 3 to 09:00 for gap < 180; same account on machine 2)
can't reach their target branches under fail-closed validation:
- Entry slots frozen to canonical anchors → slot tampering fires MANIFEST_IDENTITY_MISMATCH
  before the gap check.
- `machine_blocks == 3` per machine → a 3-block manifest split 2+1 across machines is
  rejected up front (2 blocks on one machine).
- SourceConfig enforces globally unique account ids AND rows (rows 1-6 across ALL
  machines) → the picker cannot emit a 2-machine lane; derive machine 2 by cloning a
  1-machine pick's blocks/entries and re-hashing every machine-bound field (this is the
  shape a future fleet source will emit).
- Entry-level `account_blocks` in validate_manifest fails closed first → the
  block-structure `account_blocks_idx` branch is only reachable via a direct
  `_validate_block_structure(payload, None)` call; document in the test docstring why an
  end-to-end call would be masked (it would pass on old code too).

Find the OBSERVABLE difference instead of forcing the literal shape: fix 1's real bug =
valid 2-machine manifest REJECTED (global `sorted(blocks, block_index)` compares
cross-machine pairs with negative gaps → false UNSCHEDULABLE_CAPACITY) → the RED test
asserts ACCEPT. Fix 2's fail-open only shows AFTER fix 1: staged run (gap fixed, account
key still `(machine, account)`) → duplicate account accepted, "DID NOT RAISE" — that
intermediate failure is the account bug's cleanest RED evidence. Use intermediate fix
states as RED evidence to isolate each bug.

## Full identity re-hash chain (hermes_cron manifest/picker) — order matters

Tampering ANY identity field requires re-hashing the whole chain; assignment_id FIRST,
then all entry/block ids against the NEW manifest_id:
1. `block["seed"] = machine_day_seed(day, machine, payload_seed)` — changing machine
   REQUIRES seed re-derivation (validated unconditionally).
2. `block_id = block_id_for(day, block_index, machine, account)`.
3. `entry_id = entry_id_for(manifest_id, account, machine, serial, account_row, slot_time,
   action_type, seed, block_id, session_index)`; `idempotency = f"{manifest_id}|{entry_id}"`.
4. `block["entry_ids"] = [s1.entry_id, s2.entry_id]` (session_index order).
5. `assignment_id = assignment_id_for(day, timezone, seed, owner_id, worker_id,
   source_revision, CONSTRAINTS, account_ids=sorted(entry_accounts ∪ skipped_accounts),
   state_digest (None for "0"*64), generation, resource_mapping=_resource_mapping(resources,
   entries))` — resource_mapping embeds account/machine/serial/feed_machines per entry, so
   any account/machine change invalidates it → recompute assignment_id, THEN re-hash all
   entry/block ids against the new manifest_id (mirror build_manifest_payload).
6. Sync every dict-equality-bound field on block + entries: feed.machines, feed.row,
   lock.machine, lock.serial, due/post shapes.