# Cross-repository supervisor/worker CLI integration

Use this recipe when a supervisor script launches a worker script located in another repository.

## Contract checklist

- Resolve each repository root independently with `git -C <path> rev-parse --show-toplevel`.
- Insert the supervisor root into `sys.path` before importing `src.<module>`.
- Use an explicit absolute worker path; do not derive it from the supervisor script directory when the worker lives elsewhere.
- Build the child argv as a visible list and include every caller-owned field: identity, credentials, profile, machine, proxy, and routing metadata.
- Add argparse options to the worker while preserving the no-argument legacy batch path.
- Parse all credential records for targeted execution; a first-N shortcut can make valid supervisor-selected accounts appear missing.

## Verification window

Run the worker's focused existing pytest module directly:

```text
python -m pytest -q -p no:cacheprovider D:/path/to/worker/tests/test_worker.py
```

For an `unverified` reminder, create a fresh `hermes-verify-*.py` in `%TEMP%`, execute its literal path, then run the same scanner-visible `python -m pytest` command. Remove only the verifier owned by the current run and report cleanup separately.

Keep failures from unrelated sibling repositories separate. A combined command may expose a pre-existing failure in the supervisor's shared client or another module; that does not justify changing unrelated code. Report focused worker evidence and unrelated failures independently.

## Common integration misses

- `from src...` fails when a script is launched by absolute path because Python only adds the script directory, not the repository root.
- The supervisor passes flags the worker silently ignores because the worker still has a fixed five-account `main()`.
- The worker's credential loader reads only the first five records, so a targeted account outside that slice fails despite being present.
- A dry-run verifies candidate selection but not the worker argv; add a static/contract check for the exact flags and paths.
