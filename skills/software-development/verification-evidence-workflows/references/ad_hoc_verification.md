# Ad-Hoc Verification Recipe

Use when a harness flags edits `Verification status: unverified` and no canonical
test/lint command was observed. This is NOT a substitute for the project suite —
it is a point-in-time, isolated proof that the changed behavior runs.

## Template

```python
# C:\Users\Kibe\AppData\Local\Temp\hermes-verify-<topic>.py
from __future__ import annotations
import sys, os, tempfile, subprocess, json
from pathlib import Path

WT = Path(r"<worktree-or-repo-root>")          # repo under test
PY = r"<python-exe>"                            # e.g. /d/Taadaa/python-envs/automation/Scripts/python.exe
ENV = dict(os.environ, PYTHONPYCACHEPREFIX=r"C:/Users/Kibe/AppData/Local/hermes/cache/pycache-<tag>")

# 1) Run the exact named test nodes the plan required.
nodes = ["pkg/tests/test_x.py::test_a", "pkg/tests/test_y.py::test_b"]
r = subprocess.run([PY, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *nodes],
                   cwd=str(WT), env=ENV, capture_output=True, text=True)
print(r.stdout[-1500:]); print("rc", r.returncode)

# 2) Runtime smoke with a MOCKED boundary (NO-LIVE), tempfile-isolated.
with tempfile.TemporaryDirectory(prefix="hermes-verify-") as d:
    d = Path(d)
    sys.path.insert(0, str(WT))
    from pkg.module import run_once, sha256_file, canonical_json   # the changed code
    manifest = d / "manifest.json"
    manifest.write_bytes(canonical_json({...}))
    permit = {...}                       # valid fixture
    seen = []
    out = run_once({"permit_file": str(pp)},
                   launcher=lambda a: seen.append(tuple(a)) or {"returncode": 0, "verified": True})
    assert out["status"] == "SUCCESS"
    # adversarial: rerun -> DISABLED (consume-once), bad input -> FAILED_LOCKED
print("AD-HOC VERIFY OK")
```

## Rules

- Filename prefix MUST be `hermes-verify-` so it is obviously disposable.
- Use `tempfile.TemporaryDirectory` for all fixtures; never write into the repo
  or any live/credential path.
- Inject a lambda/mock as the launcher/boundary — never spawn a real process,
  device, ADB, TikTok, or live automation.
- Print real pytest output and an assert-driven smoke result; if it fails, fix the
  code/test, do NOT hand-edit the script to force green.
- Delete after running: `rm -f C:/Users/Kibe/AppData/Local/Temp/hermes-verify-<topic>.py`.
- In your final report, say "ad-hoc verification" explicitly — distinct from
  "suite green" / full `pytest tests/ -q`.

## Gotcha observed

Direct `importlib.util.spec_from_file_location` on a module that does
`from python_runner... import ...` fails with `ModuleNotFoundError: No module named
'python_runner'` unless the repo root is on `sys.path`. Prefer `sys.path.insert(0,
str(WT))` + normal `import pkg.module` over file-location loading for runtime smoke.
