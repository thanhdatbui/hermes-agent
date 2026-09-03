# Fresh ad-hoc verification on Windows

Use this when a harness reports `unverified` and no canonical test/lint/build command is detected, especially after a code-editing session.

## Recipe

1. Create the script path with Python's `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=...)`; do not hand-pick a filename.
2. Write a narrow probe that imports the repository's source explicitly (`sys.path.insert(0, r"D:\\Taadaa\\automation-core\\src")`) so an editable install or stale site-package cannot mask the working tree.
3. Exercise the changed behavior with fakes: inspect defaults, record forwarded keyword arguments, and assert safety-sensitive invariants such as an unchanged screencap timeout. Never call ADB, a device, an account, a workbook, or another live integration.
4. Run the script with the repository's Python, capture the real exit code/output, then remove the temp file and verify it is gone.
5. Report it explicitly as **ad-hoc verification**, not as a green suite. If a full suite was attempted but blocked by collection/environment or an unrelated baseline failure, state the concrete blocker separately.

## Pitfalls

- A first probe can fail because the probe stub returns the recorded value instead of the intended result; fix the probe and rerun rather than treating that as product evidence.
- `PYTHONPATH=src` may still leave repository helper modules shadowed by an installed regular package (for example, a `tools` package). Treat that as a collection blocker, not as a product failure; use targeted probes or an explicit import path.
- Clean the temporary script even when the probe fails; use a `finally` cleanup path where practical.
