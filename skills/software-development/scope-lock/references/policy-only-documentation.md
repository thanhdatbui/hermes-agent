# Policy-only documentation checklist

Use this when updating repository policy/workflow docs without changing source,
tests, or runtime configuration.

## Contract

- Goal: make only the requested policy correction.
- Allowlist: exact policy paths named by the user.
- Forbidden: explicitly excluded policy files, code, tests, generated/runtime
  artifacts, and any path not required by the request.
- Stop: after marker checks, scoped diff review, and `git diff --check`; do not
  commit or push unless explicitly requested.

## Safe sequence

1. Read every user-named source document first.
2. Capture `git status --short --untracked-files=all`, including staged and
   unstaged path sets. Do not treat foreign dirt as ownership or as a clean-tree
   requirement.
3. Bind each requested change to a unique heading/neighboring block. Patch
   narrowly; preserve EOL/BOM and all surrounding policy text.
4. Re-read the changed regions and inspect the complete diff. Check exact marker
   counts, canonical cross-references, and explicit exclusions.
5. Run:

   ```bash
   git diff --check -- <policy-file-1> <policy-file-2>
   git diff --name-only -- <policy-file-1> <policy-file-2>
   git status --short --untracked-files=all
   ```

6. Report exact changed policy files, unchanged excluded files, preserved
   unrelated paths, and real command results. Never stage just to make a diff
   check pass when the contract says no commit/push.

## Scoped commit/push policy pattern

When the documentation defines a scoped commit/push rule, verify that it
explicitly contains: user-explicit-request precondition; allowlist/write ledger;
path-scoped staging with no `git add -A` or `git commit -a`; temporary index
separation for foreign staged paths; staged diff, reviewer, and focused
verification gates; fetch/rev-list overlap analysis; conditional
`pull --rebase --autostash`; current-upstream push and remote-SHA verification;
and exact refusal conditions. It must also say that unrelated dirty, staged, and
untracked files, a non-clean worktree, and unrelated test failures are preserved
and are not refusal reasons.

## Farm-alert G3 wording

A normal reviewed commit/push of the exact task-contract allowlist is routine
and is not a G3 question gate. G3 remains reserved for deployment, paid,
destructive, irreversible, account-mutating, or other live durable actions.
