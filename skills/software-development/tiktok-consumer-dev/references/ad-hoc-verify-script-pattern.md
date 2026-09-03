# Ad-hoc verification scripts (hermes-verify-* pattern)

When the harness reports "Verification status: unverified" for edited files with
no canonical test command, or when you need focused behavior verification, write
a temporary script under `C:\\Users\\Kibe\\AppData\\Local\\Temp` via
`tempfile.mkstemp(prefix="hermes-verify-", dir=tempfile.gettempdir())` with the
exact prefix and an OS-safe path. Run it with the CLEAN machine Python312, then
remove it in a `finally` block even when the verifier fails. Print an explicit
cleanup result. Summarize the result as **ad-hoc verification**, not suite green.
The verifier must assert behavior at the changed seam (for example, a timeout
reaches 60 seconds using fake ADB and a fake monotonic clock without a live
device), not merely import or marker presence.

## Working skeleton (Python312 clean, NOT hermes venv)

```python
import tempfile, os, textwrap, subprocess

script = textwrap.dedent('''
    import sys
    sys.path.insert(0, r"D:\\Taadaa\\Tiktok_Reg")
    sys.path.insert(0, r"D:\\Taadaa\\Hotmail")
    import py_compile
    py_compile.compile(r"...\\social_reg_v1.py", doraise=True)
    # ... behavior asserts ...
    import pytest
    rc = pytest.main(["-q", "--no-header", "--no-summary", r"...\\tests\\test_x.py"])
    assert rc == 0
    print("ADHOC_VERIFY_OK")
''')
fd, path = tempfile.mkstemp(prefix="hermes-verify-", suffix=".py",
                            dir=os.environ.get("TEMP", tempfile.gettempdir()))
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(script)
env = dict(os.environ)
env["PYTHONPATH"] = r"D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail"
env["PYTHONIOENCODING"] = "utf-8"
r = subprocess.run([r"C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe", path],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env=env, timeout=300)
print(r.returncode, r.stdout[-2500:], r.stderr[-800:])
os.remove(path)
```

## Critical pitfalls (learned 2026-08-05)

1. **Run with the machine Python312, never the hermes venv.** The hermes venv's
   PIL is broken (`ImportError: cannot import name '_imaging'`); the clean
   Python312 (the same one the runner uses) imports fine. Bare `python` in
   git-bash resolves to the hermes venv — always use the absolute Python312 path
   or `env -i` with a clean PATH.
2. **Monkeypatching module globals inside the verify script pollutes later
   pytest runs in the SAME process.** If you `social.enter_otp_code = fake` and
   then run pytest in-process, other tests that exercise the real function fail.
   Save the originals and restore in a `finally` block, or run behavior asserts
   in a separate subprocess from the pytest subprocess.
3. **Verify behavior, not just "marker present".** Assert the actual branch
   outcome (e.g. dead mail → `mark_mail_die_in_audit_pending` + source removal
   called; live mail → neither called), not merely that a string exists in src.
4. `PYTHONIOENCODING=utf-8` avoids cp1252 `UnicodeEncodeError` when printing
   Vietnamese diagnostics.
5. **The verify script's OWN assertions can be wrong — audit the script before
   blaming the code under test.** Happened twice in one session (2026-08-08)
   while checking that no raw `shell("input","swipe",...)` survived outside a
   helper: (a) an exclusion filter matched the line `"def swipe("` but the
   helper's shell call is a MULTI-LINE call, so the first line
   `device_id, "input", "swipe",` inside the helper body was counted as a
   stray "outside" call; (b) a substring check `'"input", "swipe"' in
   helper_body` ran against `helper_body` AFTER it had been converted to
   `splitlines()` — a list — so the containment test was always False. Both
   FAILs were script bugs, not code bugs; the code was fine. When a FAIL
   appears, re-read the check's own logic first: slice boundaries, list-vs-
   string containment, helper-body inclusion/exclusion, `int()` casts of
   captured args. If you need BOTH a substring check and a line-set comparison
   on the same source slice, keep the raw string AND a separate `splitlines()`
   copy. Only after the script checks out, investigate the changed code.
6. **If the wrapper is generated from a shell command, prefer forward-slash
   Windows paths inside the generated Python source** (for example,
   `D:/CodexRuntime/.../python.exe`). This avoids an intermediate quoting layer
   turning `\t` or `\v` in a backslash path into control characters. Keep the
   temporary-path creation OS-safe via `tempfile`; then clean the file after
   either outcome and report the result only as ad-hoc verification.

## Static launcher contract checks (added 2026-08-10)

For a launcher-only change where live execution is prohibited, keep the verifier
read-only and inspect the real argument-building branches instead of merely
checking that the flag string exists somewhere in the file:

1. Read the launcher with its BOM-aware encoding and normalize CRLF only in a
   separate matching copy. Assert BOM/EOL bytes independently so the check cannot
   hide an encoding regression.
2. Slice the `$arguments` builder into `PreflightOnly`, `ProfileSmoke`, and live
   branches. Assert the live branch contains the enabling flag exactly once and
   outside the `RecoveryMode` conditional, proving normal and recovery live child
   launches both receive it.
3. Assert preflight/profile branches retain their mode-specific flags and do not
   receive the enabling flag or `--no-dry-run`.
4. Keep the regression test name in the source as a second guard, but do not run
   the launcher, open TikTok, touch a device, reboot, read a workbook, or inspect
   runtime credentials/logs for this static verification.

This branch-boundary pattern catches the design regression where a recovery
ladder is implemented in the state machine but the normal batch launcher silently
omits the enabling argument. Report the result as ad-hoc verification unless the
canonical suite itself was run and its output is available.
