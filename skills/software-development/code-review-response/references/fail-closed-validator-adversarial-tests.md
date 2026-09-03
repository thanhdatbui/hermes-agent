# Adversarial Tests for Fail-Closed Multi-Gate Validators (anti gate-masking)

Case: closing audit findings on `validate_manifest` (hermes_cron, `D:\Taadaa\tiktok-luot nuoi acc`,
commit edcb71f). The validator is a chain of gates, each raising a specific ReasonCode:
structural key-set → canonical day gate → canonical lane parity → lock/entry binding →
machine↔serial consistency → source mapping → block-source binding. A tamper test that
mutates many fields at once and only asserts `pytest.raises(ValueError)` cannot prove WHICH
gate caught the attack — an early gate (day, slots, pair gap) can fire before the binding
under test, "masking" it. The audit asked for tests that cannot be gate-masked.

## Design rules that worked

1. **Mutate ONE field per test** (parametrize over the field list). Re-hash only the
   dependent ids (block_id / entry_ids / idempotency_key) — mirror the picker's derivation
   EXACTLY (`build_manifest_payload`'s rehash loop), never hand-roll a variant.
2. **Keep the non-target topology canonical** — payload day, block_index, session_slots,
   pair_gap, and entry slot times must stay valid so day/slot gates cannot fire first.
   A rehash helper docstring should say exactly this ("callers must keep day/slot topology
   valid").
3. **Sync ALL bound metadata, not just the obvious fields.** This codebase's lesson: mutating
   an entry's `serial` without also updating `entry["lock"]["serial"]` makes the lock-binding
   gate (`_validate_entry`: `lock == {...,"serial": entry["serial"], ...}`) raise
   `MANIFEST_IDENTITY_MISMATCH` BEFORE the intended source-mapping gate. A test-design fix
   (sync the lock), NOT a production weakening. Same class: `feed.machines`, `lock.machine`.
4. **Assert the exact reason code** (`excinfo.value.args[0] == ReasonCode.X.value`), never a
   bare `pytest.raises(ValueError)`. Reason codes are the contract; a wrong code means a
   different gate fired (gate-masking) or the test's expected gate is unreachable.
5. **Know the gate ORDER to predict the code.** Observed ordering (higher fires first):
   - `block.day != payload.day` → SOURCE_CONFIG_INVALID (canonical day gate, unconditional)
   - `block.lane != lane_for_day(block_day)` → SOURCE_CONFIG_INVALID (canonical parity, unconditional)
   - entry `lock` vs entry fields → MANIFEST_IDENTITY_MISMATCH
   - entry account_block reuse → MANIFEST_IDENTITY_MISMATCH
   - machine↔serial consistency across entries → MAPPING_CONFLICT
   - source mapping (entry-level and block-level row/machine/serial vs SourceConfig) → MAPPING_CONFLICT
   - entry_ids order/rehash → MANIFEST_IDENTITY_MISMATCH
   Consequence: a `serial` splice lands MAPPING_CONFLICT, but a `lane` splice lands
   SOURCE_CONFIG_INVALID (canonical gate before any source check) — assert what the code
   actually does and comment why.

## Fixture calibration vs production weakening

When a NEW unconditional canonical check (audit finding) rejects a legacy forge fixture,
the fixture — not the gate — is usually the outdated half:

- R10's machine-999 forge mutated `block["machine"]/["serial"]` and re-hashed ids but left
  the block `seed` at the original machine-1 value. The new unconditional
  `seed == machine_day_seed(day, machine, payload_seed)` check correctly rejected it at
  `validate_manifest(forged, None)` — before the test's intended watcher gate.
- Fix: calibrate the FORGE to be canonical for its new shape — rehash the block seed to
  `machine_day_seed(day, 999, payload_seed)` — and re-verify the test's original intent still
  holds (watcher still rejects the manifest at the source-config gate). Keep asserting both
  halves: the seed-canonical forge PASSES source-less validation AND is REJECTED against a
  real source (MAPPING_CONFLICT at the machine-resources gate).
- Never loosen the new gate to keep a stale fixture green; never delete the test. If the
  calibration touches a file outside the allowlist, commit it with the fix (a split commit
  leaves HEAD red) and FLAG the scope deviation prominently in the report for coordinator
  review.

## RED evidence

Capture the failure BEFORE the production change: seed-only source-less tamper ran
"DID NOT RAISE ValueError" under the old `if source is not None` guard — that transcript is
the RED proof that the test is live and the gate was missing, not that the test is wrong.

## Read-verify loop

Run the new/parametrized tests against the UNCHANGED production code first and read every
result: an unexpected reason code on a single-field mutation is nearly always a missing
dependency sync or a canonical gate firing first — diagnose, don't rewrite the assertion
to match (unless the production gate genuinely fires earlier with a defensible code, then
assert that code and comment why).