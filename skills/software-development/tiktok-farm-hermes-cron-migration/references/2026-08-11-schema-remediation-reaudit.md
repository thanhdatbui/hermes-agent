# Schema-remediation re-audit: source-less integrity and gate-masking

## Trigger
Use this reference when a manifest/schema remediation claims to close tampering, canonical ordering, or SourceConfig binding. A green suite is necessary but not sufficient: independently replay the attack shape against a valid picker-generated payload.

## Required probe matrix

1. **Untouched control**
   - Generate a real payload through the repository picker and validate it with the real `SourceConfig`.
   - Validate the same payload with `source=None` when that API is supported.
   - Record both results; never hand-build the fixture if the picker/test fixture can generate one.

2. **Source-less derived-value tamper**
   - Change one derived canonical value (first choice: block `seed`) while leaving topology and IDs otherwise valid.
   - Run `validate_manifest(payload, None)`.
   - Expected: rejection at the canonical-integrity gate. A guard shaped like `if source is not None and check(...)` is a bypass unless the value genuinely requires source authorization.

3. **Independent metadata mutations**
   - Mutate one field per probe: `account`, `machine`, `serial`, `account_row`, `day`, `lane`, `seed`.
   - Recompute only dependent `block_id`, `entry_id`, and `idempotency_key` values so the mutation survives earlier hash gates.
   - Keep day/session slots/topology valid for binding checks; use a separate boundary test for day changes.
   - Validate against the real source and assert the exact rejection reason (`MANIFEST_IDENTITY_MISMATCH`, `MAPPING_CONFLICT`, or `SOURCE_CONFIG_INVALID`).
   - A test that changes all fields at once and only asserts `ValueError` is gate-masked and does not prove source binding.

4. **Ordered identity**
   - Untampered `entry_ids` must equal `[session_1_entry_id, session_2_entry_id]` and pass.
   - Swap the list without changing its members; expect exact canonical-order rejection. `sorted()`/set equality is insufficient.

5. **Source-binding attack shape**
   - Change a mapping field such as `serial` or `account_row` and update entry metadata plus dependent hashes while keeping day, block index, session slots, and pair gap valid.
   - Validate with the real `SourceConfig`; rejection must come from source mapping, not an earlier malformed-shape gate.

## Gate-masking checklist

For each adversarial test, identify the intended validator branch and prove earlier gates remain satisfied:

- required key set unchanged;
- canonical date and session slots valid;
- block/entry IDs recomputed with the actual manifest identity;
- entry order/index valid;
- source state revisions and assignment identity consistent;
- exact exception/reason asserted.

If a finding is accepted only because an earlier gate fails, classify it as a test-quality gap, not closure of the intended invariant.

## Coordinator verification sequence

After a worker reports completion, run independently:

```text
git log --oneline -3
git show --stat HEAD
pytest <exact phase suite>
py_compile <changed modules and tests>
git diff HEAD^ HEAD --check
grep/AST probes for the targeted bypass
```

Then dispatch a fresh read-only re-audit. Do not promote a phase from REJECT/MINOR_FIXES to APPROVED based on worker self-report, exit code, or an ad-hoc probe alone.

## Provenance note

A commit may show a full-file addition when the parent did not track the module. Check `git log --follow` and `git ls-tree <parent> -- <path>` before treating that as scope creep. Separate provenance from semantic behavior.
