# Terra fallback and binding remediation

## Failure matrix

| Symptom | Root cause | Required proof |
|---|---|---|
| Focused tests pass but reviewer rejects integrity | Worker summary trusted without re-reading live anchors | Coordinator reruns focused pytest, `py_compile`, and `git diff --check` after every worker edit |
| Terra bypass can be called by another internal path | Model restriction exists only in `_post_full_context` | `_post(..., bypass_payload_guard=True)` parses payload model itself and enforces exact `cx/gpt-5.6-terra-high` plus `TERRA_MAX_PAYLOAD_BYTES` |
| Review SHA claims binding but payload changed | Caller-supplied SHA is trusted | Hash the exact bytes/UTF-8 representation that is serialized and sent; compare candidate, binding, and review hashes |
| Non-targeted mode crashes or rejects unexpectedly | New targeted variables/checks were not initialized for legacy flow | Real temporary Git test for staged, worktree, committed, and default `--repo` flow |
| Root commit fails | `HEAD~1` does not exist; `diff-tree` without `--root` returns no files | Use `diff-tree --root`; compare parent list and use the empty-tree object for a root commit |
| Partial committed scope is reviewed | `targets <= HEAD files` accepts extra files in the commit | Require exact set equality or fail closed; regression test commits target plus extra file then requests target only |
| Large default diff fails binding before Terra fallback | Binding hashes pre-truncation raw bytes while review hashes truncated text | Hash the final representation sent to reviewer, or route full context before truncation; never compare incompatible representations |
| Provider fallback error still allows partial approval | Transport failure silently falls through to truncated Sol review | Return typed `UNKNOWN`/unavailable, `passed=False`, and preserve fallback error/original byte telemetry |

## Minimal offline recipes

1. Create a temporary local Git repo with `git init`, local identity, and one or more commits; never use a device or network.
2. Test staged and worktree candidates with the same hermetic flags: `--binary --no-color --no-ext-diff --no-textconv` and `core.quotepath=off`.
3. Test a root commit and a multi-file commit with a partial `--files` list.
4. Test a non-UTF-8/binary diff and an oversized candidate. Assert either that the exact canonical payload hash matches or that the gate rejects with explicit evidence; never silently substitute bytes.
5. Mock only the HTTP response. Assert posted model, full-diff tail marker, payload size metadata, SHA fields, fallback error, and final verdict.
6. After patching, run the focused suite, compilation, and whitespace checks. Then run the scoped Closeout Gate; a score below 85 is remediation state, not completion.

## Policy boundary

A reviewer may criticize a user-defined policy, but it cannot override the active contract. Preserve rubric `overall_score >= 85` overriding advisory `ready_to_close=false`, while preserving explicit `NEED_CONTEXT:` fail-closed behavior. Record the reviewer field for telemetry rather than silently changing the contract.
