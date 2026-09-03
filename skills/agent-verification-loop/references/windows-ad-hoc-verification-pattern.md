# Windows ad-hoc verification pattern — exact recipe used in session 2026-08-27

This is the exact self-contained verification pattern that worked for the current task scope (scripts/sync-tik-workbooks.py + python_runner/tests/test_sync_tik_workbooks_lock_order.py) on Windows with MSYS git-bash.

## Driver script (written via tempfile.NamedTemporaryFile)

```python
import ast
import os
import pathlib
import subprocess
import sys

root = pathlib.Path.cwd()
env = os.environ.copy()
env["PYTHONPATH"] = ""
env["PYTHONDONTWRITEBYTECODE"] = "1"
env["PYTHONPYCACHEPREFIX"] = os.environ["HERMES_VERIFY_PYCACHE"]

def run(label, argv):
    proc = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True)
    print(f"[{label}] exit={proc.returncode}")
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

run("pytest", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
               "python_runner/tests/test_sync_tik_workbooks_lock_order.py"])
run("py_compile", [sys.executable, "-m", "py_compile",
                   "scripts/sync-tik-workbooks.py",
                   "python_runner/tests/test_sync_tik_workbooks_lock_order.py"])
for rel in ("scripts/sync-tik-workbooks.py",
            "python_runner/tests/test_sync_tik_workbooks_lock_order.py"):
    ast.parse((root / rel).read_text(encoding="utf-8"), filename=rel)
    print(f"[AST] OK {rel}")
run("git-diff-check", ["git", "diff", "--check", "--",
                       "scripts/sync-tik-workbooks.py",
                       "python_runner/tests/test_sync_tik_workbooks_lock_order.py"])
print("[verifier] all checks passed")
```

## Launcher (single terminal call, no intermediate files left behind)

```python
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

worktree = pathlib.Path.cwd()
temp_root = pathlib.Path(tempfile.gettempdir())
preexisting = set(temp_root.glob('hermes-verify-*.py'))
pycache_root = pathlib.Path(tempfile.mkdtemp(prefix='hermes-verify-pycache-'))
verifier = None
try:
    with tempfile.NamedTemporaryFile(prefix='hermes-verify-', suffix='.py',
                                     dir=temp_root, mode='w', encoding='utf-8',
                                     delete=False) as f:
        verifier = pathlib.Path(f.name)
        f.write(<driver source above>)
    env = os.environ.copy()
    env['HERMES_VERIFY_PYCACHE'] = str(pycache_root)
    proc = subprocess.run([sys.executable, str(verifier)],
                          cwd=worktree, env=env, text=True)
    exit_code = proc.returncode
finally:
    if verifier is not None:
        verifier.unlink(missing_ok=True)
    shutil.rmtree(pycache_root, ignore_errors=True)
    remaining = set(temp_root.glob('hermes-verify-*.py'))
    print(f'[cleanup] verifier_absent={not verifier or not verifier.exists()} '
          f'pycache_absent={not pycache_root.exists()} '
          f'preexisting_preserved={preexisting.issubset(remaining)}')
raise SystemExit(exit_code)
```

## Output this run produced (ad-hoc verification — NOT full suite green)

```
[pytest] exit=0
35 passed, 8 skipped in 7.34s
[py_compile] exit=0
[AST] OK scripts/sync-tik-workbooks.py
[AST] OK python_runner/tests/test_sync_tik_workbooks_lock_order.py
[git-diff-check] exit=0
[verifier] all checks passed
[cleanup] verifier_absent=True pycache_absent=True preexisting_preserved=True
```

## Key points

- **Same-turn freshness**: verifier runs in the same turn as the last edit.
- **No pytest.main()**: spawns fresh `python -m pytest` subprocess; avoids multiprocessing deadlocks.
- **PYTHONPATH cleared**: prevents hermes venv pollution (PIL/_imaging cp311 vs cp312 mismatch on this host).
- **Cleanup verified**: verifier file + pycache removed; preexisting `hermes-verify-*.py` preserved.
- **Explicit labels**: every check labeled; counts and exit codes reported.
- **Scope-locked**: only the two allowlisted files are checked.