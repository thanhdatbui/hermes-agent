# CRLF-Safe Surgical Multi-File Edits (consumer repos)

Pattern proven 2026-08-08 on Tiktok_Reg (jitter Phase A: social_reg_v1.py 5 call sites,
tiktok_login_v1.py 1 site + import, test file +2 tests). Applies to any Windows consumer
repo where files are CRLF or **mixed** CRLF/LF and git must show zero line-ending churn.

## When to use
- Task constraint says "giữ CRLF" / "keep line endings" / "no line-ending churn".
- Multiple edits across files with exact line anchors from an audited plan.
- Files may be mixed CRLF/LF (tiktok_login_v1.py was 751 CRLF + 103 LF-only lines!).

## Workflow (proven order)

1. **Baseline snapshot BEFORE any edit** (save to `D:\Taadaa\jitter-baseline-<ts>.txt`):
   - `git status --short` for the target files (note which were ALREADY dirty from other sessions — test file here had 50 pre-existing uncommitted lines; don't claim them as yours)
   - `git diff` for target files
   - `sha256sum` each file
   - CRLF count: `python -c "d=open(f,'rb').read(); print(f, d.count(b'\r\n'), d.count(b'\n')-d.count(b'\r\n'))"`
2. **Backup** to a dir OUTSIDE the repo: `cp <3 files> /d/Taadaa/jitter-backup-<ts>/`.
3. **Check per-line endings** of every anchor line BEFORE constructing byte patterns — do NOT assume all-CRLF. Mixed files have LF-only lines adjacent to CRLF lines.
4. **Edit with a Python script operating on bytes** — never sed, never the patch tool for line-ending-sensitive edits:
   - read `rb`, split on `b'\n'` (each element keeps its trailing `\r` if CRLF)
   - `repl_line(path, lines, lineno, expected, new, tag)` that ASSERTS `lines[lineno-1] == expected` before replacing — the content assert is what catches line-number drift (see Pitfalls)
   - rejoin with `b'\n'`, assert `out.count(b'\r\n') == expected_delta`, write `wb`
   - make it **idempotent**: `if actual == new: skip` so a re-run after a mid-script failure doesn't corrupt
5. **Verify after**:
   - sha256 + CRLF count again; CRLF delta must equal exactly the number of added lines (e.g. 751→753 = +2 import lines), LF-only count unchanged
   - `git diff --stat` on the 3 files only — confirm no other files in YOUR delta (repo may have 30+ dirty files from other sessions; distinguish yours)
   - `git diff` visually: only content lines change, no whole-file rewrite
   - semantic scan: `rg -n '"input", "tap"' *.py` — every call site must contain the wrapper; note out-of-scope files (calibrate.py had non-jitter taps) and do NOT touch them, report as out-of-scope
   - run the focused test file first (`13 passed`), then broader suite; if suite is device/network-bound (>10 min, pre-existing collection errors), run the related subset and report precisely — do not claim full-suite green

## Pitfalls (all hit in the wild)

- **Line numbers shift after insertions.** Adding 2 import lines shifted the tap site 440→442; the content assert in `repl_line` caught it on the first run (script aborted before writing that file — safe). Fix: re-derive line numbers after any insertion, or rely on content asserts instead of raw line numbers.
- **Dual import blocks.** tiktok_login_v1.py has `if __package__:` and `else:` twin import blocks (lines ~20-25 and ~60-65). Tests import top-level → the `else` branch is the LIVE path. Add the new name to BOTH blocks or you get NameError at runtime while tests still pass (lazy function body).
- **Mixed line endings in one file.** Splitting on `b'\n'` and preserving trailing `\r` per element handles it; verify LF-only count is unchanged after edit.
- **f-strings can't contain `\r\n` escapes** in the edit script itself — compute counts into variables first.
- **Fuzzy patch tools normalize endings** — for CRLF-sensitive edits use the byte script, not the patch tool.
- **File may already be dirty** from another session — snapshot baseline first so your delta is provably only your edits; never "revert" or claim the pre-existing diff.
- Also: **Windows python.exe rejects MSYS paths** — `python /d/Taadaa/apply_jitter_gmail.py` fails with `can't open file 'C:\d\Taadaa\...'` because native python.exe doesn't understand `/d/...`. MSYS paths work for bash builtins/rg but NOT for the Windows interpreter — invoke as `python 'D:/Taadaa/script.py'` (forward slashes + drive letter) or the native backslash path. `sh` in git-bash, not `cmd`; the script itself (edit scripts live OUTSIDE the repo, e.g. `D:\Taadaa\`) should use forward-slash Windows paths inside the Python strings too.
- **`import random` at top of file** — check the top-of-file combined imports BEFORE adding a new import; a mid-file duplicate `import random` later in the script is then left untouched (minimal diff), not removed and not duplicated.

## Text-mode recipe for ONE file with BOM + mixed EOL (proven 2026-08-08 gmail_reg_v10.py)

gmail_reg_v10.py: UTF-8 **BOM** + 4991 CRLF + 26 bare LF. For 3 small edits in a single file the byte-split approach is overkill — read with `newline=''` so text stays byte-faithful, and let `utf-8` (NOT `utf-8-sig`) keep the BOM as the leading `\ufeff` char:

```python
with open(path, "r", encoding="utf-8", newline="") as f:   # newline='' => zero translation; BOM survives as \ufeff
    data = f.read()
assert data[0] == "\ufeff", "BOM missing"
CR = "\r\n"
old = "def tap(device_id, x, y, wait=None):" + CR
assert data.count(old) == 1, f"anchor count={data.count(old)}"   # uniqueness guard => no silent double-wrap
data = data.replace(old, new_text_with_CRLF + CR + CR + old)
# ... repeat per anchor ...
with open(path, "w", encoding="utf-8", newline="") as f:        # \ufeff re-encodes to BOM bytes on write
    f.write(data)
```

- Anchors must carry the file's OWN EOL (`\r\n` suffix); a bare-LF anchor cannot match CRLF lines.
- After edit, byte-check: `d.count(b'\r\n') == baseline + len(new_lines_added)` (4991→4996 for +5 lines), bare-LF count UNCHANGED (26), `d[:3] == b'\xef\xbb\xbf'`.
- Sanity-test the helper function itself (e.g. `_jitter`) by exec'ing ONLY its extracted def lines from a line-based slice — a greedy `re.search(r'def x.*?return .*', re.S)` captures beyond the function and NameErrors on module-level constants.

## Replay-determinism proof (strongest edit verification)

For edits applied by a transform script, the strongest evidence is: **re-apply the transform to the PRE-EDIT backup bytes and assert the result == current file bytes**. Byte-identity proves the transform is the sole source of the current state — zero drift, EOL untouched. Pair with the **idempotence guard**: assert the old un-replaced anchors no longer exist in the current file, so a re-run would refuse (its `count == 1` asserts fail) instead of double-wrapping. Proven 2026-08-08 (gmail jitter round 2: `replay(backup_bytes) == current_bytes` — 205252 == 205252 bytes, all 8 checks pass). This also satisfies a "fresh verification evidence" gate for the transform script itself without re-touching the target.

## Prompt-template chains & N-identical anchors (proven 2026-08-08 recovery_runtime.py)

Task: append one sentence to each of 4 worker prompt templates in a single CRLF file
(`python_runner/scheduler/recovery_runtime.py` — pure CRLF, 0 bare LF, 2959 lines). The
two repair prompts end with the SAME sentence, and the two advisor prompts end with the
SAME sentence → each anchor occurs exactly 2×.

### Anchor on the last string line + closing paren (implicit string concat)

Each prompt is a Python implicit string-concatenation chain:
```python
prompt = (
    "Act as the bounded recovery patch owner. ... "
    "For MANUAL_NEEDED_POPUP, ... into success."\r\n
        )\r\n
```
To append a sentence to the chain, the anchor must span the last line AND the closing
paren so the new quoted line lands inside the parens with matching indent (12 spaces here):
```python
repair_old = (... + '"\r\n        )')          # last string line + CRLF + 8-space ')' line
repair_new = (... + '"\r\n            "' + SENT + '"\r\n        )')
```
A new line is inserted; `data.replace(old, new)` naturally keeps the chain valid.

### N-identical anchors → replace-all with count asserts on BOTH sides

```python
assert data.count(repair_old.encode("utf-8")) == 2, "repair anchor count != 2"
data = data.replace(repair_old.encode("utf-8"), repair_new.encode("utf-8"))
assert data.count(repair_new.encode("utf-8")) == 2  # post-check: every block got the sentence
```
`grep -c "<anchor text>" file.py` on the source first confirms the expected N (here 2, 2).
Never use a uniqueness guard (`count == 1`) when N>1 blocks are identical — the assert
message should name the family so a drift is diagnosable.

### Proving "only additions" when the file was ALREADY dirty

This file had a pre-existing uncommitted schema diff (1+/6−) from an earlier session.
`git diff --stat` after your edit shows 5 insertions/6 deletions — NOT "only additions" —
unless you attribute the delta. Capture BEFORE editing, then compare:
```bash
git diff --stat python_runner/scheduler/recovery_runtime.py   # baseline: 1+/6-
# ...edit...
git diff --stat python_runner/scheduler/recovery_runtime.py   # after: 5+/6-
git diff python_runner/scheduler/recovery_runtime.py | grep "^@@"   # hunk map
```
The hunk map is the cleanest attribution: each `@@ -N,M +N',M' @@` hunk whose context
matches your edit region is yours; the baseline hunk (here `-2210,12 +2210,7` = the schema
relaxation) is pre-existing. Report: "my delta is purely additive: 4 insertions, 0 deletions;
the 6 deletions are the pre-existing schema change (baseline captured first)". Do NOT revert
or claim the pre-existing diff.

### Edit script hygiene (two real failures this session)

- The edit script itself must be py_compile-clean BEFORE running: first draft referenced
  undefined names (`SENT` vs `SENTENCE`, `n_lf_before`) and had a typo'd enum string
  ("PATCHES_READY" instead of "PATCH_READY"). It never executed (path error below) — the
  rewrite with `\u`-escapes for the Vietnamese payload ran clean. Prefer `\u`-escapes for
  non-ASCII payloads in the edit script; keep enum/identifier spellings in a variable so
  typos can't silently diverge between blocks.
- **New MSYS path-mangling variant**: `python3 /c/Users/Kibe/_edit_recovery_prompt.py`
  from a `D:\...` cwd fails with `can't open file 'D:\c\Users\Kibe\...'` — the interpreter
  prepends the current drive to the `/c/...` path. Invoke with the forward-slash drive form:
  `python3 "C:/Users/Kibe/_edit_recovery_prompt.py"`. (Same root cause as the documented
  `/d/...` → `C:\d\...` case; `/c/...` from a non-C: cwd is the other direction.)
- Paths containing SPACES (`D:\Taadaa\tiktok-luot nuoi acc`): `read_file` handles them
  fine; `search_files` may fail to resolve them (rg "system cannot find the path"). Fall
  back to quoted terminal: `cd "/d/Taadaa/tiktok-luot nuoi acc" && grep -n ...`.

## write_file edit-script traps — JSON escape + raw strings (proven 2026-08-09 Tiktok-video)

Editing `state_machine.py` (pure CRLF, 10932 lines) via a python transform script authored
with the `write_file` tool: the tool's JSON parameter decoding turns every `\"` you type
into a real `"` in the file — a patch script written with escaped quotes (`"...\"..."`)
lands with unterminated string literals (write_file lint flags it, but only after you've
typed the whole thing).

- **Write snippet blocks as RAW triple-quoted strings** `r'''...'''` in the edit script.
  No `\"` escapes needed at any layer; the JSON round-trip is lossless; the script is
  py_compile-clean on first write.
- **Backslash-bearing source anchors require raw strings.** File source text like
  `caption.replace("#", "\\#")` contains TWO backslashes on disk; a normal Python literal
  collapses `\\` → `\` and the anchor never matches (`found 0 occurrences`). Raw strings
  keep both backslashes literal. Real newlines inside the raw block are actual newlines —
  convert with `.replace('\n', NL)` where `NL = '\r\n'` for CRLF files.
- **The `'\n' + block` prefix trap.** When inserting with `'\n' + new_block`, that literal
  LF is NOT converted by the `.replace('\n', NL)` applied to `new_block` — the file ends
  with exactly ONE bare LF in otherwise pure CRLF (same for a `'\n'` glued between two
  converted blocks). Verify after EVERY write with a bare-LF regex on bytes:
  `len(re.findall(b'(?<!\r)\n', data)) == 0`, and repair the exact spots
  (`\r\n\n` → `\r\n\r\n`, `)\n-` → `)\r\n-`) rather than re-running a full transform.
- **Fail-fast uniqueness guard**: `assert content.count(old) == 1` per anchor inside the
  transform — a typo'd/duplicate anchor aborts the whole script before any file is written
  (ran 5/7 edits OK, then aborted cleanly on edit 5 with `found 0 occurrences` — file
  untouched, no partial write).
- Probe ALL target files' CRLF/LF counts BEFORE editing (state_machine.py 10932 CRLF/0 LF;
  tests/test_tiktok_workflow.py LF-only; docs CRLF) — each file keeps its own dialect,
  never assume one EOL per repo.

### Verification for this repo's recovery tests

```bash
python3 -m py_compile python_runner/scheduler/recovery_runtime.py   # COMPILE_OK
python3 -m pytest python_runner/tests/test_recovery_supervisor.py \
  python_runner/tests/test_recovery_runtime_hermes_parser.py \
  python_runner/tests/test_recovery_classification.py \
  python_runner/tests/test_recovery_runtime_audit.py \
  python_runner/tests/test_recovery_handlers.py -q
```
Observed: `99 passed, 8 subtests passed in 10.48s` (98 expected baseline + 1 classification
test). Report the exact added sentence per method, the test tail, the diff --stat with
attribution, and the bare-LF count (0 before/after).
