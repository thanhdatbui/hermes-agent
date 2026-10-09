# Policy-edit verification checklist

Use for exact-scope markdown policy plus focused-validator tasks.

1. Bind Git operations to the directory that actually contains `.git`; a parent workspace may be only a container. Verify `git rev-parse --show-toplevel` before scoped status/diff commands.
2. Preserve the exact allowlist. For a policy/validator pair, inspect and modify only those two files; do not touch the production gate or candidate code.
3. Treat policy text and validator tests as one contract: retain existing tests, add marker tests for every required invariant/state/class, and add runtime parser tests only through the existing public API when production edits are forbidden.
4. On the Windows Hermes terminal, a foreground command request with an explicit timeout above 60 seconds is rejected before execution. Use `timeout <= 60` for a focused command, or use a tracked background process when the command may exceed that bound. A parameter rejection is harness setup, not test evidence.
5. After the final edit, execute the exact focused pytest command, then compile/diff checks as separately reported evidence. If the command never starts, report verification as incomplete; never infer a pass from prior output.

For this class of task, the canonical focused command is:
`python -m pytest <absolute-test-path> -q -p no:cacheprovider`

Keep this reference session-agnostic: it records the verification boundary and scope discipline, not a particular policy document or candidate.
