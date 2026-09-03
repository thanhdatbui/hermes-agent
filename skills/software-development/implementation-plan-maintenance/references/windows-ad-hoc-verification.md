# Windows focused ad-hoc verification

Use this when an external verification guard says the workspace is unverified and no canonical test command was detected.

```python
from pathlib import Path
import os, subprocess, sys, tempfile

repo = Path.cwd()
script = '''import os, sys
sys.path.insert(0, os.getcwd())
import pytest
raise SystemExit(pytest.main(["-q", *NODES]))
'''
path = None
try:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".py", prefix="hermes-verify-",
        dir=tempfile.gettempdir(), delete=False,
    ) as handle:
        handle.write(script)
        path = Path(handle.name)
    result = subprocess.run([sys.executable, str(path)], cwd=repo, text=True)
    raise SystemExit(result.returncode)
finally:
    if path is not None:
        path.unlink(missing_ok=True)
```

Keep `sys.path.insert(0, os.getcwd())`: a temp script otherwise makes `%TEMP%` the import root and can cause `ModuleNotFoundError` during pytest collection. Run only the changed-behavior nodes, clean up in `finally`, and report the result as **focused ad-hoc verification**, never as full-suite green.
