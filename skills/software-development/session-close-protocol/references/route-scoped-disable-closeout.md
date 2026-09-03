# Route-scoped disable closeouts

Use this reference when closing a fix that disables an automated side effect for one producer route (for example, a Farm Alerts recovery spawn) while preserving sibling routes.

## Evidence matrix

| Boundary | Required proof | Failure interpretation |
|---|---|---|
| Producer | Alert/banner/screenshot path still runs; only the named spawn seam is guarded | Missing delivery proof means the fix may have muted the alert, not just recovery |
| Consumer | Direct callers are enumerated; no blanket guard is added to a shared `run()`/entrypoint | An unconditional consumer return is scope drift |
| Runtime | Production interpreter and imported module path are identified; source and runtime bytes/hashes are compared | Source-only verification can be false-green when an installed copy is executing |
| Candidate | Reviewer sees the exact current production diff and focused test, including removed lines | A verdict from an earlier candidate is stale after any edit |
| Release | Only the explicit allowlist is staged; post-rebase test/diff gate passes; remote SHA equals local SHA | Dirty unrelated paths are preserved, not cleaned or absorbed |

## Recommended sequence

1. Freeze `goal`, route-level scope, non-goals, acceptance criteria, repository/branch/upstream, and every protected dirty path.
2. Trace the route from producer to side effect. Prefer the narrowest producer seam when the consumer has other legitimate callers.
3. Check runtime provenance with the interpreter used by the automation, then compare source/runtime raw hashes. If a runtime copy was hot-patched, save a backup outside Git and report that fact separately from the source commit.
4. Run an offline focused probe that stubs Telegram/ADB/process boundaries. Assert both: (a) alert delivery remains observable, and (b) the named recovery spawn is not called.
5. Run the independent reviewer on the exact current candidate. If it rejects blanket scope, remove only the offending consumer change, byte-compare that file to `HEAD`, and re-audit; do not weaken the reviewer contract or keep unrelated changes for convenience.
6. Stage explicit production/test paths only. Inspect `git diff --cached --name-status` and `git diff --cached --check` before committing.
7. For a dirty primary worktree, use a clean temporary worktree from `origin/<branch>` to run the real `pull --rebase`, final test, and push. This avoids stashing/resetting protected local files. Prove the pushed tree matches the intended local tree before aligning/removing the temporary branch/worktree.
8. Verify `git ls-remote` equals the pushed commit SHA, then remove only self-created temporary worktrees/branches. Re-check protected dirty paths and runtime/process state.

## Common failure patterns

- **Symptom fix became global disable:** a guard at `consumer.run()` stopped every caller, not only the Farm Alerts invocation. Treat this as a logic rejection even when the producer test is green.
- **Undo left invisible drift:** removing a guard can leave a missing/extra blank line or EOL change. Compare raw bytes and SHA-256 against `HEAD` before claiming the path is reverted.
- **Source/runtime mismatch:** the repository source can be patched while the farm interpreter imports a site-packages copy. Verify both locations and do not claim runtime effect from source tests alone.
- **Stale approval:** a reviewer approved an earlier diff, then a later edit changed the candidate. Any post-verdict edit requires a fresh exact-diff review and fresh tests.

Keep secrets, bot tokens, credentials, screenshots, logs, and runtime state out of the reference and out of Git.
