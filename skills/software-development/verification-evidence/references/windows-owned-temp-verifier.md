# Windows owned-temp verifier recipe

Use this when a harness reports `verification status: unverified` after a code edit.

## Ownership-safe sequence

1. Before creating anything, snapshot the existing temp verifier names:
   `Path(tempfile.gettempdir()).glob("hermes-verify-*.py")`.
2. Track exact paths created by this turn. Never delete the entire glob: old
   verifier files may belong to another session/worker.
3. Prefer a small launcher written outside the repository over nested
   `python -c` multiline quoting in Git-Bash. The launcher should:
   - create the real probe with
     `NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)`;
   - write a focused NO-LIVE probe against the changed seam;
   - run it with repository `cwd` and explicit `sys.path`/environment;
   - print exit code and captured output;
   - unlink the owned probe in `finally`.
4. Delete the owned launcher after it exits and verify both owned paths are
   absent. Preserve any pre-existing temp verifier files and report them
   separately.

## Harness-failure classification

A syntax error from generated quoting, such as `unterminated string literal` or
`unexpected character after line continuation`, is `HARNESS_SETUP_FAILURE`, not
product evidence. Fix the launcher/probe representation and rerun. Do not edit
production or claim a failed product verification from that first attempt.

## Minimal detector probe

For a process detector, mock `subprocess.run`, feed stdout lines for machine 11,
12, exact machine 1, `--machine=1`, a cross-line false combination, and a token
boundary such as `1foo`. Assert the expected booleans and the exception fail-open
path. Report this as **ad-hoc verification**; it does not replace canonical
pytest/module/full-suite evidence.
