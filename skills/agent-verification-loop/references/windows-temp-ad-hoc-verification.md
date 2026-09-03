# Windows temporary ad-hoc verification recipe

Use this when the workspace/system reports `unverified` after a code or test edit, or when no canonical test command is detected.

1. Create a driver with `tempfile.mkstemp(prefix="hermes-verify-", suffix=".py", dir=r"C:\Users\<user>\AppData\Local\Temp")`.
2. Create a separate `tempfile.mkdtemp(prefix="hermes-verify-pycache-", dir=...)` and set `PYTHONPYCACHEPREFIX` to it.
3. The driver must spawn a fresh interpreter with `subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", ...], ...)`; do not call `pytest.main()` in-process.
4. If the environment injects a conflicting `PYTHONPATH`, remove it in the child environment so the requested interpreter resolves its own installed dependencies. This is a setup workaround, not a persistent prohibition.
5. Run the thinnest tests covering the changed behavior in the same turn as the edit. Report it as **ad-hoc verification**, not suite green.
6. In `finally`, unlink the driver and remove only the temporary pycache created by that invocation when possible. Verify the driver is absent. Prefer making steps 1–6 one self-cleaning terminal invocation so the verifier itself is not left in the harness Changed paths; a verifier write is not evidence until the fresh subprocess has run.
7. If a selected node is parametrized, copy its collected node ID or invoke the parent node. Do not hand-write an empty parameter suffix such as `...[ ]`; that produces a collection error rather than verification evidence.

Record the exact command, pass/deselected counts, exit code, cleanup result, and any concrete blocker. Do not manufacture a result from an earlier run.
