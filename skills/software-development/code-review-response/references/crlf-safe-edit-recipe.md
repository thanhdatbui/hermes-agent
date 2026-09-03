# CRLF-safe edit recipe (pure-CRLF source files)

Used 2026-08 on `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py`
(CRLF THUẦN — user forbids the patch tool/sed on it) and
`docs/tiktok-ui-compatibility.md` (CRLF). Test files in the same repo are LF-pure,
so they may be edited with the patch tool — but verify EOLs first (`file`).

## 1. Probe the transport before authoring a big edit script

`write_file`/skill payloads carry backslash escapes as LITERAL text:

- payload `\n` → file bytes `\` `n` → Python string value = real newline (works for LF scripts)
- payload `\r\n` → file bytes `\` `r` `\` `n` → Python string value = real CRLF (works for CRLF-building scripts)
- a RAW newline inside a single-quoted string literal → real LF in file → SyntaxError

Probe:
```bash
python - <<'PY'
data = open('probe.py','rb').read()
print(repr(data))          # confirm escape transport before relying on it
print(hex(data[0]))
PY
```

## 2. Lossless LF↔CRLF round-trip (preferred, pure-CRLF targets)

```python
PATH = r"D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py"
with open(PATH, "rb") as fh:
    raw = fh.read()
text = raw.decode("utf-8")
assert text.count("\r\n") > 0, "file is not CRLF"
assert "\n" not in text.replace("\r\n", ""), "file has lone LF — not pure"
text = text.replace("\r\n", "\n")          # normalize ONCE

def edit(old: str, new: str, tag: str) -> None:
    global text
    assert old in text, f"[{tag}] OLD NOT FOUND"
    assert text.count(old) == 1, f"[{tag}] OLD NOT UNIQUE ({text.count(old)})"
    text = text.replace(old, new, 1)

# ... edit() calls with plain "\n"-joined old/new strings (no \r anywhere) ...

with open(PATH, "wb") as fh:
    fh.write(text.replace("\n", "\r\n").encode("utf-8"))   # convert back
```

Discipline:
- `cp file /tmp/sm_backup.py` first; a failed edit leaves the file untouched only if the script
  raises BEFORE the final write — so put all `assert`s before `open(..., "wb")`.
- The edit script itself may be LF; only the target's EOLs matter.

## 3. Verify afterwards

```bash
file scripts/tiktok_workflow/state_machine.py      # must still say "CRLF line terminators"
python - <<'PY'
txt = open('scripts/tiktok_workflow/state_machine.py','rb').read().decode('utf-8')
print('CRLF:', txt.count('\r\n'), 'lone LF:', txt.count('\n') - txt.count('\r\n'),
      'lone CR:', txt.count('\r') - txt.count('\r\n'))
import py_compile; py_compile.compile('scripts/tiktok_workflow/state_machine.py', doraise=True)
PY
```

## 4. Run the suite before writing new tests (triage, don't wave off)

Full suite first: `PYTHONPATH=D:/Taadaa/Tiktok-video/scripts <venv>/Scripts/python.exe -m pytest tests/test_tiktok_workflow.py -q -p no:cacheprovider`
Expected-break buckets:

- (a) Old test mocks the old lenient contract → update mocks for the new API,
      keep the test name/assertion (e.g. set `machine.context.soft_reboot_recovery_outcome =
      "ATTEMPTED_FAILED"`, add `machine._package_is_foreground = lambda *_: True`,
      draw ≥5% dark pixels in a synthetic strip screenshot).
- (b) New gate mock absent → add it.
- (c) Real bug from the refactor → fix the code (this session: `_caption_chunk_landed`
      had no whole-dump visible-text fallback when the dump lacked an `EditText`-class node).

Structured-signal pattern for "ambiguous False" findings: classifier returns an enum
(`VERIFIED/ATTEMPTED_FAILED/NOT_ELIGIBLE/EVIDENCE_MISSING/ALREADY_CONSUMED/NOT_RESERVED`),
stored on the context; callers gate on the allowed subset; every denied branch logs why.
Per-error-code budgets live in a dict (`atx_kill_signatures[signature] = True`), with
evidence lists persisted per signature (`atx_kill_evidence[signature] += [{timestamp,
handler, transition, attempts, before_artifact, after_artifact}]`).

## 5. Pitfall: `Path.read_text()` hides CRLF

`read_text()` runs universal-newlines: it TRANSLATES CRLF → LF in memory. Consequences (hit
in the ui-compatibility round-4 pass):

- `repr()`-dumped lines show only `\n` even though `file` says "CRLF line terminators" — you
  cannot infer the true EOL layout from them, and `old` search strings built from those dumps
  silently never match (`assert text.count(old) == 1` → 0).
- ALWAYS do search/replace and EOL proofs on `read_bytes().decode("utf-8")`; when you did use
  `read_text()`, re-add `\r\n` explicitly to any multi-line `old` string before counting.
- Cross-check every CRLF assumption with byte counting, not repr displays:
  `b = open(p, "rb").read(); print(b.count(b"\r\n"), b.count(b"\n") - b.count(b"\r\n"))`.

## 6. Heredoc caution for CRLF-building scripts

Bash `<<'PY'` heredocs pass bytes verbatim, but Windows console/`git-bash` encoding can mangle
Vietnamese/UTF-8 in replacement strings and a `\\n`-looking payload can land as a real newline.
When a patch script must emit escaped text, prefer `write_file` (documented escape transport)
over heredoc, and ALWAYS verify the output immediately — `python -c "import ast;
ast.parse(open(f).read())"` or `pytest --collect-only` — before trusting the edit.
