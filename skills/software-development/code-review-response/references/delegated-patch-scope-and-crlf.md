# Delegated Patch Scope and CRLF Reverification Recipe

Use this recipe when a delegated worker edits a dirty Windows repository and the patch touches a CRLF-pure source file.

## 1. Establish the boundary

- Capture `git status --short` and the target-file diff before accepting the worker report.
- Treat unrelated dirty files as pre-existing. Do not reset, revert, or clean them.
- Compare each changed helper against `git show HEAD:<file>` to identify collateral behavior changes.

## 2. Repair a malformed CRLF block safely

Use a temporary Python script authored with `write_file`, not a large shell heredoc:

```python
from pathlib import Path
p = Path(r"D:\repo\module.py")
data = p.read_bytes()
assert data.count(b"\r\n") == data.count(b"\n")
start = data.index(b"unique start anchor")
end = data.index(b"unique end anchor", start)
old = data[start:end]
# Build replacement with explicit CRLF and assert expected indentation/content.
new = b"..."
out = data[:start] + new + data[end:]
assert out.count(b"\r\n") == out.count(b"\n")
p.write_bytes(out)
```

Always assert anchor occurrence counts before writing. Re-read the edited region after the script runs. Delete the temporary script and verify it no longer exists.

## 3. Triage regressions

- Run the focused finding tests after compile succeeds.
- If a focused test exposes an unrelated worker change, restore only that function/block from `HEAD` using a byte-preserving extraction; retain the intended finding fix.
- For fail-closed OTP routing, distinguish the authoritative newest-row reader from stale CDP/browser preview fallbacks. Test both the no-old-code guarantee and the mailbox-health path.

## 4. Release evidence

Run, in order:

1. `env -u PYTHONPATH python -m py_compile <changed modules>`
2. focused pytest selection
3. `git diff --check`
4. full suite with `env -u PYTHONPATH python -m pytest tests/ -x -vv`

Report focused and full-suite results separately. A full-suite failure caused by an out-of-scope baseline symbol/test is a blocker, not a passing release gate; do not claim live readiness.
