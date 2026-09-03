# Phase 9A.1 identity verification recipe

Use this reference when migrating `SourceConfig` identity from globally unique `account_row` to composite `(machine, account_row)`.

## Required sequence

1. Read repository instructions and the approved plan.
2. Record the exact R5 regression command and real pre-write count. A historical count is context only, never a baseline assertion.
3. Add the focused test before production edits. Run the single test against unchanged production and preserve the expected RED reason (`MAPPING_CONFLICT` from global row uniqueness).
4. Implement the minimal change: compare `(machine, account_row)` identities; do not alter `account_id`, machine↔serial, or row-range validation.
5. Run focused GREEN, then the exact R5 command again. Compare counts numerically to the captured baseline.
6. Run compile, `git diff --check`, and an allowlist-only diff/status inspection.
7. If the task is commit-only, perform a live exact-path preflight before staging: requested files must exist in the current worktree, and the requested source must differ from `HEAD`. Missing paths, stale `.pyc` files, historical plan references, or copies in another worktree do not satisfy the request. Stop without staging or committing rather than reconstructing files or making a no-op commit.
8. For a valid commit, stage only the explicit allowlist, assert `git diff --cached --name-only` is exactly that list, run `git diff --cached --check`, commit the exact message, then inspect committed names/status. Do not push or touch unrelated dirty/untracked files.

## Focused behavior matrix

- Accept: two accounts with the same `account_row` on different machines and different serials.
- Reject: duplicate `(machine, account_row)` with `MAPPING_CONFLICT`.
- Reject: duplicate `account_id` even when machine/row differs.
- Reject: one machine mapped to multiple serials or one serial mapped to multiple machines.
- Reject: row values outside the `require_row` range.

## Fresh ad-hoc evidence

When a verification gate asks for a temporary probe, create it with Python's `tempfile.NamedTemporaryFile` using `prefix="hermes-verify-"`, `suffix=".py"`, `delete=False`, and `dir=tempfile.gettempdir()`. Run it with the repository root explicitly inserted into `sys.path`, because a script located in Temp otherwise sets `sys.path[0]` to Temp. Keep the probe offline and import the real changed module. Print a concise behavior count and delete the file in `finally`; report cleanup failure with the exact path.

Before declaring the probe valid, assert that the imported production module resolves under the requested absolute worktree (for example, compare `Path(module.__file__).resolve()` against the target repo root). This prevents a Temp probe from silently importing a same-named module from another checkout or stale installation. If the self-check fails, classify it as a setup/worktree blocker, not a behavior pass.

Treat every later verification request as a fresh evidence gate. Re-check absolute target-path existence immediately before the focused command and immediately before reporting. If the requested focused test file is absent, a canonical suite pass that omits it is not focused-test evidence; diagnose the live worktree rather than inferring that an earlier write persisted or reconstructing a missing test from history.

Label the result **ad-hoc verification**. It is supplemental evidence and does not replace the canonical focused suite, R5 suite, compile, diff-check, or allowlist inspection.

## Evidence labels

- RED: focused test failed on unchanged production for the expected missing behavior.
- GREEN/canonical: repository-defined command with real pass count.
- Ad-hoc verification: temporary independent probe with behavior count and cleanup status.
- Setup blocker: dependency/interpreter/environment issue; do not convert it into a test pass.
