# Jitter core tap_element — automation-core 0.4.38 (2026-08-08)

Session detail for the "jitter core tap primitives (anti-detect)" change,
implemented from `D:\Taadaa\CORE_JITTER_PLAN_20260808.md` (luna APPROVED +
Sol APPROVED). Complements the SKILL.md "Safe multi-file CODE edits" section.

## Design (as approved)

- `src/automation_core/input.py`:
  - `import random` added (before `import re`, alphabetical).
  - `_jitter(coord: int, max_offset: int) -> int`:
    `coord + random.choice((-1, 1)) * random.randint(4, max_offset)` (±4..6px
    with default max 6; never ±0 — range is always nonzero).
  - `tap_element(adb, element, *, jitter_max_offset: int = 6)` — when
    `jitter_max_offset > 0` jitter BOTH x and y; `0` = exact old behavior
    (opt-out for coordinate evidence-bound paths).
  - `tap_selector(adb, xml_text, selector, *, jitter_max_offset: int = 6)`
    pass-through to tap_element.
  - Default 6 covers all consumers going through core primitives.
- `src/automation_core/tiktok_popup.py`: `dismiss_popup(..., *,
  jitter_max_offset: int = 6)`; both `tap_element(adb, checkbox)` (~199) and
  `tap_element(adb, button)` (~224) forward it.
- `tests/test_tiktok_popup.py`: the 9 tests asserting LITERAL coordinates
  (`50,25 / 996,150 / 102,174 / 92,138 / 60,35+170,35 / 557,1134 /
  545,1080+557,1200`) now call `dismiss_popup(adb, jitter_max_offset=0)` —
  literals kept EXACTLY, zero relaxation. `test_unmatched_text_returns_no_match`
  (no coordinate assert) stays `dismiss_popup(adb)`.
- `tests/test_input_jitter.py` (new, 4 tests):
  `test_tap_element_jitters_within_6px` (50 iterations, |x-cx|∈[4,6],
  |y-cy|∈[4,6], no global random.seed), `test_tap_element_jitter_zero_keeps_center`
  (literal center), `test_tap_selector_passes_jitter` (both opt-out and default),
  `test_dismiss_popup_forwards_jitter` (jitter=0 → literal 50,25; default →
  within ±6 of (50,25); use the 2-dump iterator pattern from test_tiktok_popup).
- `CHANGELOG.md`: `## 0.4.38 - 2026-08-08` (anti-detect jitter, default ON,
  opt-out jitter=0). `pyproject.toml`: one-line version 0.4.37 → 0.4.38.
- `__init__.py` untouched (export signatures unchanged, backward compatible).

## Evidence-bound rule (do not regress)

USB popup evidence (270,81 — COMPAT-USB-001) never goes through tap_element
(usb_popup.py shells directly) → naturally unfazed. Test literal coordinates in
test_tiktok_popup.py are EVIDENCE-BOUND → always pass `jitter_max_offset=0`.

## EOL ground truth (baseline, per file)

| file | git eol | working | edit notes |
|---|---|---|---|
| src/automation_core/input.py | i/lf w/lf | 0 CRLF / 45 LF | insert with LF |
| src/automation_core/tiktok_popup.py | i/lf w/crlf | 246 CRLF / 0 LF | anchors are single-line → byte replace safe |
| tests/test_tiktok_popup.py | i/lf w/crlf | 282 CRLF / 0 LF | split on b'\ndef test_' per-test blocks; replace only tests containing `["input", "tap",` literal |
| CHANGELOG.md | i/lf w/mixed | 141 CRLF / 9 LF | TOP block is LF (`# Changelog\n\n## 0.4.37...`); insert new section with LF |
| pyproject.toml | i/lf w/mixed | 22 CRLF / 1 LF | version line is the single LF line |

Note: git HEAD pyproject.toml version was **0.4.43** (working copy already
downgraded to 0.4.37 by another session's dirty state) — only change the one
version line, do not touch the rest.

## Verify matrix (all real output)

1. `PYTHONPATH=src python -m pytest tests/test_tiktok_popup.py tests/test_input_jitter.py -q` → **20 passed**.
2. `PYTHONPATH=src python -m pytest tests/test_usb_popup.py tests/test_usb_debugging.py tests/test_ui_dump.py -q` → **30 passed**.
3. `python -m py_compile src/automation_core/input.py src/automation_core/tiktok_popup.py tests/test_input_jitter.py tests/test_tiktok_popup.py` → OK.
4. `git diff --stat` scoped to the 5 tracked files → only intended hunks; new file shows untracked.
5. EOL counts after edit identical to baseline (CRLF counts unchanged per file).
6. Double-jitter grep over consumers (Tiktok_Reg, register gmail, Tiktok-video,
   tiktok-luot nuoi acc, tiktok-add-bao-mat-f2a, Hotmail, tiktok-log-in):
   `rg -n '"input", "tap"'` → no matches; consumers route through core
   primitives so core jitter covers them (no double layer).
7. Full suite: 461 passed, 2 failed — both PRE-EXISTING (test_startup,
   test_tiktok_benign_popup: neither imports tap_element/dismiss_popup/input;
   both files dirty in other sessions). test_package_metadata.py collection
   error = missing `tools.verify_wheel_metadata` module (env, unrelated).

## Incident timeline (why the SKILL.md warnings exist)

1. First edit attempt via long bash heredoc → PermissionError on `'wb'` open
   of input.py + bash "unexpected end of file from `{'` (heredoc too long).
2. Debug probe script tested `'wb'` on REAL `tiktok_popup.py` → wrote b'TEST',
   truncating 246 lines → 4 bytes. Detected via grep/wc = 0 lines.
3. Restored from `D:\Taadaa\core-jitter-backup-20260808-065706\`; a careless
   `cp $B/a.py $B/b.py .` dumped 3 files at repo root (wrong destinations) —
   caught ONLY by sha256-vs-baseline comparison (`core-jitter-baseline-20260808-065706.txt`).
4. Rewrote edit script as `write_safe()` (write `path+'.jittmp'` → `os.replace`)
   and applied all 6-file edits cleanly. New tests initially failed on
   `call[:3]`/index mistakes → fixed → 20 passed.

## Artifacts

- Baseline: `D:\Taadaa\core-jitter-baseline-20260808-065706.txt`
- Backup: `D:\Taadaa\core-jitter-backup-20260808-065706\`
- Edit script (retired): `D:\Taadaa\core-jitter-edit.py`
- No commit was made (per task instruction).
