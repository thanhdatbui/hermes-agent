# Exact Patch, Budget, and EOL Recovery

Use this reference when a delegated coding task provides an exact allowlist, integration anchor, bounded tool/iteration budget, and mandatory final commands.

## Checklist

1. Count skill loads, baseline commands, reads, failed calls, writes, and verification calls against the stated budget. Reserve enough calls for the production integration, test assertion/fixture edit, and every required final command.
2. Read only the allowlisted files and exact anchors. Preserve unrelated dirty paths; do not spend budget on broad status dumps or repository archaeology.
3. Wire the production boundary before accepting helper-only or test-only progress. Verify the once-per-invocation guard survives loop continuations and is placed only at the final answer boundary.
4. Compare raw EOL bytes against the actual repository blob before converting anything. Use `git show HEAD:<path>`, raw `CRLF`/`LF` counts, `git diff --numstat`, and `git diff --ignore-space-at-eol --numstat`. If the prompt's stated baseline conflicts with `HEAD`, report the contradiction and do not normalize speculatively.
5. Run the exact named commands after the final edit. Earlier output is stale after any source, test, or EOL change. If the budget expires before the final commands, report partial/incomplete and enumerate the missing checks.

## Failure pattern

A worker may spend its budget on status, EOL conversions, and exploratory diff output, then leave the requested integration unwired and the required test/compile/diff checks unrun. A large numstat can be line-ending churn, but the repository's actual `HEAD` encoding is authoritative for the candidate. Do not claim that a helper-only diff or a normalized file is a completed patch.
