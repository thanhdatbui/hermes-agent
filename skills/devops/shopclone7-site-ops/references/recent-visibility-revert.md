# Recent visibility rollback — evidence-first procedure

Use when the user says “revert only products enabled recently”, not “hide all”.

## Why current status is insufficient

`products.status` has no built-in audit history. A current `status=1` row does not prove it was recently enabled. Do not infer a target set from IDs, create time, or current counts alone.

## Evidence order

1. Look for the exact prior operation evidence: pre-change backup, manifest, SQL condition, session transcript, or an earlier read-only product-ID list.
2. Prefer an explicit prior target-ID set that records the transition `0→1`.
3. If the prior operation was broad but the old rows can be reconstructed from a dated snapshot, compare the snapshot to the current supplier catalog by stable product/API ID.
4. If no exact set can be proven, stop before mutation and report the ambiguity; ask whether to use a user-provided ID list or a dated snapshot.

## Scoped rollback

After exact IDs are proven, verify live identity first (for CloneFBIG: `suppliers.id=1`, `type=API_31`, matching domain). Read-only check must show every target currently belongs to that supplier and is visible. Then:

- backup only the target rows, including `id,supplier_id,status,price,cost,category_id,api_id,api_stock,api_time_update,name`;
- mutate only `status`, with an identity- and status-guarded predicate, e.g. `supplier_id=1 AND id IN (...) AND status=1`;
- verify each target is `status=0`;
- verify the known old rows remain visible;
- verify manual products (`supplier_id=0`) and other suppliers are unchanged;
- report backup path, target IDs/count, before/after counts, and any concurrent sync drift.

Never replace an evidence-backed recent-ID rollback with `UPDATE ... WHERE supplier_id=<id>` or a “last N products” heuristic. A broad hide is a different user request.
