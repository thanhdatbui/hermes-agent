# Validator-binding edit (canonical + registry lines) — 2026-08-09

Session: add the 2 binding lines to `Tiktok_Reg/AGENTS.md` + `tiktok-log-in/AGENTS.md`
so `automation-core/tools/check_ui_compatibility.py` reports 0 findings. Result:
`OK: 9/9 consumers`, exit 0; both git diffs = exactly +2 lines; EOLs preserved.
Backup in `D:\Taadaa\binding-backup-20260809-050554\` (outside any repo).

## Initial probe (before touching anything)
- `wc -l` + byte counts per file — the two files had **opposite EOLs**:
  - `Tiktok_Reg/AGENTS.md`: pure LF (176 bare LF, 0 CRLF)
  - `tiktok-log-in/AGENTS.md`: pure CRLF (124 CRLF, 0 bare LF)
  → per-file EOL in the edit script; never one shared EOL assumption.
- Anchor `## Coordinator -> direct worker boundary (canonical)` occurs exactly once
  in each file (line 16 of both).
- `grep -c -i "ui.compat\|canonical contract"` → neither file has any UI-compat
  mention yet → both flagged only for `agents_missing_canonical_binding` +
  `agents_missing_registry_binding` (registries already exist).

## Validator semantics (read the source before assuming)
`check_ui_compatibility.py`: 9 `CONSUMERS`; per consumer AGENTS.md must contain
(casefold substring):
- canonical: `ui-compatibility-contract.md`
- registry filename: `Path(consumer.registry).name.casefold()` — i.e. for the
  default registry `docs/ui-compatibility.md` the string `ui-compatibility.md`;
  Tiktok-video's custom registry means `tiktok-ui-compatibility.md`.
Registry file itself must contain the canonical name + 9 REQUIRED_CONCEPTS
markers — those checks were already passing; only the 2 AGENTS.md bindings were
missing.

## Placement rule (mandate: exactly N lines, no new header)
Reference format already in the wild:
- `Tiktok-video/AGENTS.md` ¶165-168: `## UI Compatibility Contract` section with
  the 2 bullet lines + 1 explanatory line.
- `tiktok-luot nuoi acc/AGENTS.md` ¶81-87: `## Shared UI Compatibility Binding`
  section, same 2 bullets + explanatory line about updating
  canonical/local records on any selector/popup/coordinate change.

When the task says "THÊM 2 dòng" (STRICTLY 2 lines, no section header allowed),
insert the 2 bullets immediately AFTER the anchor line (the section heading) —
deterministic, produces a bare `+2` diff (numstat `2 0` on a clean file), and
does not disturb any other section. Don't invent a header; match the task.

Bullet format (backticks around both paths, matching Tiktok-video):
```
- Canonical contract: `D:\Taadaa\automation-core\docs\ui-compatibility-contract.md`.
- Local registry: `docs/ui-compatibility.md`.          <- default registry name
```

## Baseline + backup (outside repo, incl. pre-dirty targets)
- Only modify the 2 AGENTS.md files; both repos are heavily pre-dirty.
- **`Tiktok_Reg/AGENTS.md` was ALREADY modified vs HEAD** (9 insertions / 2
  deletions before this session) → snapshot `git -C Tiktok_Reg diff AGENTS.md >`
  backup dir as `Tiktok_Reg-AGENTS-baseline.diff` (ground truth to prove post
  diff = baseline + my 2 lines only).
- `tiktok-log-in` AGENTS.md was clean vs HEAD (git diff --stat = empty).
- Everything outside AGENTS.md (e.g. `docs/ui-compatibility.md`, pre-dirty at
  165 insertions) must be proven untouched; it never gets opened by the script.

## Edit script (per-file EOL, abort-if-dirty, atomic write)
```python
import os
BACKUP = r"D:/Taadaa/binding-backup-<ts>"
ANCHOR_HEADING = "## Coordinator -> direct worker boundary (canonical)"
NEW_LINES = [
    "- Canonical contract: `D:\\Taadaa\\automation-core\\docs\\ui-compatibility-contract.md`.",
    "- Local registry: `docs/ui-compatibility.md`.",
]
JOBS = [("Tiktok_Reg-AGENTS.md", "<path>/Tiktok_Reg/AGENTS.md", "\n", "LF"),
        ("tiktok-log-in-AGENTS.md", "<path>/tiktok-log-in/AGENTS.md", "\r\n", "CRLF")]
for bak_name, path, eol, label in JOBS:
    backup = open(os.path.join(BACKUP, bak_name), "rb").read()
    data   = open(path, "rb").read()
    assert data == backup, "working copy differs from backup — ABORT"
    crlf, bare = data.count(b"\r\n"), data.count(b"\n") - data.count(b"\r\n")
    assert (bare == 0) if label == "CRLF" else (crlf == 0), f"EOL drift {path}"
    a = (ANCHOR_HEADING + eol).encode()
    assert data.count(a) == 1, f"anchor {data.count(a)}x"
    repl = a + (eol.join(NEW_LINES) + eol).encode()
    new  = data.replace(a, repl, 1)
    tmp = path + ".tmp"; open(tmp, "wb").write(new); os.replace(tmp, path)
    assert backup.replace(a, repl, 1) == new   # byte-level proof
```
Write via `write_file` (not heredoc), run `python "C:/Users/Kibe/AppData/Local/Temp/…"`
(MSYS `/c/…` gets mangled). `.tmp` + `os.replace` avoids intermittent `PermissionError`
on direct `'wb'`.

## Verification transcript (all used)
1. Byte recount: LF file 176→178 bare LF (CRLF stays 0); CRLF file 124→126
   CRLF (bare LF stays 0).
2. `grep -Fc "<string>"` → 1 per string per file. **Pitfall**: regex
   `grep -c "automation-core\\\\docs\\\\ui-compatibility-contract.md"` under
   bash double-quotes returns 0 even though the string IS present (backslash
   mangling through bash+grep regex). Always use `grep -F`/`grep -Fc` for
   backslash-containing path strings.
3. Validator: `OK: 9/9 consumers`, exit 0.
4. `git diff --numstat AGENTS.md`: clean file → `2 0`; pre-dirty file →
   `11 2` (= baseline 9/2 + my +2).
5. Pre-dirty proof: `diff <(grep '^+' backup/<file>-baseline.diff) <(grep '^+'
   after.diff)` → output `1a2,3` only (my 2 new lines); no deletions added.
6. Temp script removed; backup dir holds the 3 artifacts (2 file copies +
   baseline diff).