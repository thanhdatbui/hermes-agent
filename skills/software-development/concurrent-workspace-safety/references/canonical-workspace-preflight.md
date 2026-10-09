# Canonical Workspace Preflight

Use this read-only preflight before a delegated coding task touches source, tests, or Git state:

1. Treat the user/coordinator's exact absolute workspace as authoritative. Run `git -C <requested-path> rev-parse --show-toplevel` using the native path spelling and compare the normalized result to the requested checkout.
2. If the path is absent or is not a Git checkout, stop the implementation attempt. Report the exact path and blocker; do not edit or test another repository.
3. Run `git -C <requested-path> status --short` only after the root check succeeds. Keep the baseline bound to that checkout.
4. If any tool reports a different `cwd`, Git root, or worktree than requested, classify it as path/provenance drift. Re-bind to the explicit native path or stop; do not infer that a plausible sibling repository is the target.
5. Avoid broad home-directory scans when the workspace was explicitly supplied. They consume bounded worker budgets and can surface unrelated repositories whose dirty state, tests, and results must not be attributed to the requested task.

A missing target repository is an honest blocker, not permission to guess a replacement. The final report should distinguish `inspected`, `edited`, and `verified`; if the root check failed, all three implementation states remain unreached.