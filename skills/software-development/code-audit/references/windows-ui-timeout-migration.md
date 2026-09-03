# Windows UI-Timeout Migration Checklist

Use for a narrow UI-capture / UI-render-wait timeout increase in a Windows Python repository
(especially repos where the working tree is CRLF but the git index is LF — `core.autocrlf=true`).

## Scope probe

- Snapshot `git status --short`; do not overwrite unrelated working-tree edits.
- Enumerate `*.py` while excluding any path component named `.runtime`.
- Search for `capture_ui_xml`, literal `uiautomator dump`, and `screencap`.
- Distinguish capture budgets / UI-render waits from non-UI waits: lock/workbook, process,
  `dumpsys account`, ADB command timeouts (`ime set`, `wm size`, `pull`, `am start`, raw
  `screencap`, `tap`, `shell`, and `input`), file-transfer, device-wait and reboot timeouts
  remain unchanged unless explicitly requested. A screenshot/read wait wrapper may increase
  its polling budget while leaving the underlying atomic command timeout untouched.
- For screen capture adapters, inspect both constructor `default_timeout` and the operation's
  explicit timeout; classify each knob before changing it.

## Mixed-EOL baseline snapshot (do this FIRST)

- `git ls-files --eol -- <file>`: `i/lf w/crlf` means index is LF, working tree CRLF →
  `git show HEAD:<file>` yields LF while the working tree is CRLF. Never assume uniform EOL.
- A CRLF working tree can contain individual LF lines (written by other tools/editors).
  Snapshot `sha256sum <file>` + byte counts (crlf / lf / lone-cr) BEFORE any edit — this is
  your only restore proof once the tree differs from HEAD.

## PATCH TOOL CORRUPTS MIXED-EOL FILES (observed 2026-08)

- The `patch` tool (replace mode) normalizes the EOL of the ENTIRE changed hunk region, not
  just the replaced line: a single-line change flipped ~26 surrounding LF lines to CRLF across
  5 separate regions of `gmail_reg_v10.py`, producing a huge spurious diff. A context-rich
  `old_string` does NOT prevent this.
- On mixed-EOL / CRLF files: DO NOT use the patch tool at all. Use the guarded line-targeted
  replacement script below.

## EOL-safe edit: line-targeted byte-exact script

- Read with `splitlines(keepends=True)`; for each line keep its OWN EOL suffix (`\r\n` if the
  line ends with it, else `\n`).
- Edit by line number with a content assertion: `assert content(lines[idx]) == old`, then
  `lines[idx] = new + eol(lines[idx])`. This is collision-proof and never touches EOL bytes.
- For a multi-line transformation (e.g. `for _ in range(5):` → deadline `while`), replace one
  line with TWO lines sharing the original EOL; expect exactly +1 line in the post-write tally.
- Python gotcha: bytes literals cannot contain non-ASCII — decode the file to str (utf-8; the
  BOM survives as `\ufeff` and re-encodes intact) and edit strings, or build needles via
  `.encode('utf-8')`.
- Verify after write: EOL counts == baseline ± exactly the intended added lines, zero lone CR,
  `py_compile`, `git diff --check`, and a full `git diff` eyeball (must show only intended lines).

## Recovering baseline after patch-tool damage

- Reconstruct from git: `git show HEAD:<file>` (LF) → `.replace(b'\n', b'\r\n')` → re-apply the
  known-LF line numbers (assert each line currently ends `\r\n`, strip to `\n`) → undo any
  intentional test edits → write → assert `sha256` == the pre-edit baseline hash.
- This works ONLY because the baseline sha256 was snapshotted before the first edit.

## Regression tests for timeout contracts (AST pattern)

- New test file parses the target source with `ast` and asserts:
  1. every named wait helper's `timeout` default == new value (map args to defaults, must be
     `ast.Constant` literals);
  2. every literal `timeout=` keyword at call sites of those helpers == new value (skip
     passthroughs like `timeout=timeout`, an `ast.Name`);
  3. inline poll budgets (`time.time() + N`) == new value in the relevant source slices.
- Run RED first (must fail against old values), then GREEN after the edits.

## Ad-hoc probe: FakeClock timeout-budget verification

- To behaviorally verify a 60s wait WITHOUT waiting 60 real seconds: monkeypatch the module's
  `time` with a FakeClock (`time()` returns `t`; `sleep(s)` advances `t`). Stub the device
  calls, run the wait, assert `t` advanced exactly start+60 (budget honored) or <60 (early
  success path). This proves the loop actually polls the new budget.
- Probe pitfalls observed:
  - Restore EVERY monkeypatched symbol between probe sections — capture originals
    (`orig_x = g.x`) before the first patch. A leaked `get_ui_xml` / `find_node_in_xml` stub
    silently changes later sections' behavior and produces false probe failures.
  - Raw-string XML detectors match `package="com.android.gms"` with DOUBLE quotes — stub XML
    must use double quotes or the substring check misses (single-quote XML silently never
    matches).
  - Account for pre-loop sleeps when asserting the never-match budget (e.g. `sleep(D_MEDIUM)`
    before the deadline: expect t == start + 3 + 60).

## Reporting

- Give a per-spot table with file, current line/context, old and new values.
- State exact full-suite pass/fail counts; list unrelated pre-existing failures separately
  (prove independence: failing tests must not import the changed module).
- Label tempfile probes (prefix `hermes-verify-`) as ad-hoc verification, not suite green.
