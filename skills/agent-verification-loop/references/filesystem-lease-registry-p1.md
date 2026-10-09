# Filesystem lease-registry P1 recipe

Use this matrix when reviewing a filesystem-backed lease implementation:

| Gate | Required evidence |
|---|---|
| Canonical identity | Case-insensitive, absolute/normalized path key; aliases collide; persisted display path remains readable. |
| Per-path lookup | Mutation reads only the deterministic record for the requested path or a lease ID that encodes its record key. Unrelated corrupt JSON does not block renew/release. |
| Record integrity | Canonicalized record path hashes back to its filename; mismatch fails closed. |
| Parse boundary | Malformed JSON, wrong types, non-finite/overflow values, recursion errors, Unicode/read errors become a fail-closed result rather than escaping. |
| Ownership race | Persistent OS advisory/byte-range handle, or an equivalent atomic strategy, prevents an old owner from deleting/replacing a newer lock. |
| Publication | Acquire uses fsync plus no-replace publication (`link` or equivalent); renew/takeover may use atomic replace. |
| Contention | Real temporary filesystem with concurrent contenders; exactly one acquisition succeeds for one path. |

## Focused test set

Include tests for case-variant acquire plus renew/release, unrelated corrupt record during mutation, malformed JSON exceptions, wrong filename/path-key mismatch, and real contention. Run the focused module with `python -m pytest -q -p no:cacheprovider` and keep it under the requested time budget. Finish with path-scoped `git diff --check` and exact changed-path verification.

## Windows note

Do not mutate a lock file by opening it through a second writer while an OS byte-range lock is held; Windows correctly rejects that operation. Test replacement-race safety through competing handles/processes, and keep the lock handle open for the duration of the critical section.
