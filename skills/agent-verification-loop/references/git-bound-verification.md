# Git-Bound Verification for Mutable Worktrees

When verification depends on a Git diff or audit binding, treat extraction as a snapshot, not proof that the tree stays unchanged. A binding should carry `mode`, `base_ref`, `commit_sha`, `head_sha`, `scope`, and `scope_hash`; validate all fields before accepting evidence.

Match checks to mode semantics:

- `staged`: reject staged/unstaged overlap on every recheck, not only during initial extraction.
- `worktree_targeted`: validate only the exact target scope, including untracked target files; unrelated dirty files may remain.
- `committed` / `committed_targeted`: use the same `base_ref` range as candidate extraction and reject dirty overlap with the bound committed scope.

Re-run the binding check after tests and immediately before closeout/review acceptance. Do not rely only on a pre-test hash comparison.

Use compact real-Git temporary repositories for regressions rather than mocks: assert the initial binding passes, mutate the staged target after the simulated test, and assert the post-test binding fails closed. Add separate targeted worktree and committed-targeted cases proving unrelated dirty files are ignored while target drift and base/scope mismatches are rejected. Run focused pytest, `py_compile`, and `git diff --check` in the same verification turn.
