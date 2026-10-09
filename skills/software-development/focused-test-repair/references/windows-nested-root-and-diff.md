# Windows nested-root and external-diff triage

Use this reference when a focused repair task runs in a Windows farm repository whose apparent project directory may not be the Git root.

1. Resolve the actual root before scoped Git evidence:
   `git -C <candidate> rev-parse --show-toplevel`
2. Run `status`, `diff`, and `diff --check` against the returned root (or keep using `git -C`). An absolute pytest path can pass from a parent directory, so pytest success alone does not establish the Git working directory.
3. If Git reports `cannot spawn : No such file or directory` or `external diff died`, classify it as configured external-diff interference, not a source failure. Obtain diagnostic diff output with the external diff disabled, for example:
   `git -c diff.external= -C <repo> diff -- <allowlist>`
4. Preserve the user's exact verification command when it is contractual; use the Git override only to recover scoped diff/status evidence.

This is diagnostic guidance only: it does not relax the no-commit/no-push boundary or broaden the allowlist.