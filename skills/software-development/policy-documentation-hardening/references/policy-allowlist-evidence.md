# Policy allowlist evidence recipe

Use this after the final edit to a narrowly scoped policy/documentation allowlist.

1. Read each exact target as bytes and record SHA-256, byte count, BOM status, LF count, CRLF count, and literal marker counts.
2. Confirm the canonical block is present once and each adapter has exactly one pointer. If the literal marker must occur once, use one marker line, not matching start/end markers with the same token.
3. Run the exact scoped `git diff --check` and `git diff --numstat` commands required by the task. If no Git root is bound, report that exact limitation; never synthesize output or choose a sibling checkout.
4. Inspect the complete diff for only allowlisted paths and no EOL churn. Re-run all checks after the last write because earlier evidence is stale.
5. Preserve unrelated dirty/untracked paths and do not stage, commit, push, or touch candidate code when the task forbids it.
