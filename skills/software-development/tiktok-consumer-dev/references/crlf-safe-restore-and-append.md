# CRLF-safe restore & append in consumer repos (byte-exact Python)

Consumer files (`.py`, `docs/*.md`) are CRLF in the working tree but LF in the
git blob (autocrlf). Any block restore / doc append must be byte-exact or you
produce mixed line endings and a noisy diff. Use Python byte operations, NOT
the `patch` tool, for inserts/restores (see pitfall at the end).

## Restore a deleted block from HEAD into a CRLF working file

1. Extract the exact HEAD line range (LF, from the blob):
   `git show HEAD:<file> | sed -n '791,1054p' > /tmp/block.txt` — verify the
   first/last lines are the expected boundaries before using them.
2. Insert with Python, converting LF→CRLF and anchoring on a unique marker:

```python
import subprocess
from pathlib import Path

blob = subprocess.run(
    ["git", "show", "HEAD:python_runner/tests/test_multi_machine_feed_session.py"],
    cwd=REPO, capture_output=True, check=True,
).stdout
lines = blob.split(b"\n")
block_lines = lines[790:1054]            # 0-based: HEAD lines 791..1054
block = b"\r\n".join(block_lines) + b"\r\n"

data = TARGET.read_bytes()
anchor = b"    def <next_test_after_block>(...) -> None:\r\n"
idx = data.index(anchor)                 # insert right before the anchor def
assert <first_line_of_block> not in data  # guard against double-insert
TARGET.write_bytes(data[:idx] + block + data[idx:])
```

3. Verify: `file <target>` still says CRLF; LF-only count == 0
   (`data.count(b"\n") - data.count(b"\r\n")`); `git diff --check` clean;
   `git diff --stat` on the test file drops back to a small delta (the restore
   must NOT show the deleted tests as a removal).

## Append a docs entry (COMPAT / ui-compatibility.md) with CRLF

- Build the entry as a Python str with `\n` newlines, then
  `entry = entry.replace("\n", "\r\n")` and `TARGET.write_bytes(data + entry)`.
- Ensure the file ends with exactly one `\r\n` (append it if not) so the entry
  starts on its own line.
- Verify after write: CRLF count grew by the entry's line count and LF-only
  count is still 0.

## Pitfall: the `patch` tool DOUBLES backslashes in Windows paths

Editing a line containing a literal Windows path (e.g. `D:\OneDrive\...xlsx`
inside a docs entry) with the fuzzy `patch` tool can turn `\` into `\\` (or
`\\\\` after repeated fuzzy fixes) and mangle indentation — the matcher treats
backslashes as escapes. Symptom: `grep -n "OneDrive" file` shows doubled
slashes; `git diff --check` may still pass (it's not whitespace). Fix with a
byte-region replace in Python, not another fuzzy patch:

```python
start = data.find(b"(D:")
end = data.find(b"PROXYgandienthoai.xlsx)", start)
canonical = b"(D:\\OneDrive\\codex_gmail_debug\\PROXYgandienthoai.xlsx)"
data = data[:start] + canonical + data[end + len(b"PROXYgandienthoai.xlsx)"):]
```

Also: in bash `python3 - <<EOF` heredocs, a Windows path in a normal string
literal triggers `SyntaxWarning: invalid escape sequence '\O'` and can make an
`assert` fail even when the byte pattern is correct — use raw strings
(`r"D:\OneDrive..."`) or build the bytes via `b"..."` literals with doubled
backslashes, and assert on the region boundaries, not the full literal.

## Reference

- Working pytest invocation (hermes-venv PYTHONPATH poison):
  `env -u PYTHONPATH "/c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" -m pytest <tests> -q -p no:cacheprovider`
