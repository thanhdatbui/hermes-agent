# Exact Bounded Source-Fix Retries

When a user supplies an exact source path, known anchor, line-change cap, one focused test, and a no-live/no-commit boundary, treat it as a bounded retry—not an invitation to explore the repository.

1. Confirm the exact file resolves and inspect only that file plus scoped status/diff. If the supplied spelling/path does not resolve, fail fast and report the mismatch; do not silently substitute a similarly named checkout or broaden the search.
2. Preserve pre-existing hunks. Apply the smallest semantic patch at the named anchor, staying under the requested changed-line cap and touching no test or adjacent source file.
3. Select one already-existing focused test for the named behavior using a bounded, targeted lookup. Run only that test with the user's timeout; if it cannot be identified or started immediately, stop rather than spending the budget on broad discovery.
4. Do not commit, stage, invoke ADB/devices, or perform live actions. Return the exact diff and the test's actual stdout/stderr and exit status.

For account-switcher/manual-needed flows specifically, preserve the concrete `last_reason` or guard error supplied by the current branch. Do not replace it with a generic hardcoded `switch_reason`; the returned reason must continue to distinguish a missing switcher/account from a login/manual-needed state.

Pitfall: a Git-Bash path spelling/Unicode mismatch is a resolution blocker, not permission to guess. Verify the exact user path before editing or testing.
