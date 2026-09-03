# Source-Binding Gate-Masking Probe

Use this when a schema/manifest tamper test claims to reach a source-mapping branch but only asserts a shared error enum.

## Procedure

1. Start from a real generated payload and validate the untouched payload with the real source and with `source=None` when the API permits it.
2. Mutate one binding field at a time. Recompute every dependent identity: block ID, entry IDs, idempotency keys, ordered ID lists, and assignment/resource identity when applicable.
3. Keep unrelated canonical metadata synchronized. For entries this commonly includes `feed.row`, `feed.machines`, lock machine/serial, block metadata, validation counts, skipped-account coverage, and resource lists. Keep day, slot timestamps, pair topology, required keys, and source account coverage valid.
4. Assert the exact reason *and* prove the rejecting branch. A simple disposable Python `sys.settrace` probe can record the last validator locator before `ValueError`; alternatively wrap the source lookup or validator helper with an in-memory spy. Do not treat `MAPPING_CONFLICT` from an entry-shape check as proof of `SourceConfig` rejection.
5. Test serial and account mappings separately when both are acceptance criteria. A source-bound serial splice should synchronize entry/feed/lock fields and then reject at the source account comparison. An account splice must also update feed/account coverage bookkeeping; otherwise an earlier duplicate or feed-row gate masks source mapping.
6. For source-less integrity, verify a benign self-consistent unauthorized fixture is accepted if that is the contract, then tamper a canonical derived field (such as machine/day seed) with dependent hashes re-derived and require the exact internal-integrity reason. Temporarily bypassing the guard in memory is useful red-capable evidence; never edit the repository for this probe.

## Evidence table

| Probe | Expected evidence |
|---|---|
| baseline with source | accepted |
| benign source-less canonical fixture | accepted, authorization intentionally absent |
| seed/derived-field tamper source-less | exact internal-integrity reason; trace reaches derived-field guard |
| fully rehashed serial splice | exact source-mapping reason; trace reaches source comparison |
| fully rehashed account splice | exact source-mapping reason; no duplicate/coverage gate first |
| reversed ordered IDs | exact identity/order reason |

Always report the difference between “same reason code” and “same validation branch.”