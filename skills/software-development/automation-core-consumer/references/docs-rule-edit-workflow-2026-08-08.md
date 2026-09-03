# Spec-driven multi-file .md rule edits — recipe (2026-08-08)

Session: adding rule `ui-coordinate-fallback-after-recovery-ladder-20260808` to 8
.md files across 7 Taadaa repos, per PLAN/SPEC
(`D:\Taadaa\UI_RECOVERY_COORDINATE_FALLBACK_PLAN_20260808.md` +
`..._SPEC_20260808.md`). Result: 12 replacements in 8 files, byte-identical
verification, 0 findings introduced (4 findings proven pre-existing).

## Workflow (0→7)

0. Baseline snapshot to `D:\Taadaa\coordfallback-baseline-<ts>.txt`:
   per-repo `git status --short` + `git diff --stat`, plus `file <path>` for
   every target file (ground truth for CRLF/LF — `file` reports MIXED files as
   "with CRLF, LF line terminators").
1. Backup 8 files to `D:\Taadaa\coordfallback-backup-<ts>\` — OUTSIDE any repo.
   (`D:\Taadaa\.git` is an empty directory, not a real repo, so root-level
   artifacts are fine.)
2. Write ONE Python binary-replace script via write_file (heredoc breaks on
   quotes/unicode in git-bash; backslashes in Windows paths also get mangled —
   use forward slashes in the strings).
3. Run it: per file, per edit — assert anchor bytes occur exactly once, replace
   once, write bytes back. Per-file EOL: `s.replace('\n','\r\n')` for CRLF
   files, plain for LF files.
4. Verify byte-level: `backup_bytes + expected_replacements == current_bytes`
   for all 8 files. This is the strongest possible check — no other byte may
   have changed.
5. Grep canonical ID across all target files (spec requires it in each).
6. Run canonical validator + `git diff --stat`/`--numstat` per repo vs baseline.
7. Clean up temp scripts (they live in `%TEMP%` or repo root; delete after).

## Reusable byte-verify skeleton

```python
# Verify: backup + expected replacements == current bytes (per-file EOL).
import os
BK = r"D:\Taadaa\coordfallback-backup-20260808-004042"
JOBS = [  # (backup_filename, current_path, eol, [(tag, anchor, replacement), ...])
    ("01-....md", r"D:\Taadaa\...\file.md", "\r\n", [("1a", ANCHOR, REPL)]),
]
for bak_name, path, eol, edits in JOBS:
    cur = open(path, "rb").read()
    expected = open(os.path.join(BK, bak_name), "rb").read()
    for tag, anchor, repl in edits:
        a_b = anchor.replace("\n", eol).encode("utf-8")
        assert expected.count(a_b) == 1, f"{path} [{tag}]: anchor {expected.count(a_b)}x"
        expected = expected.replace(a_b, repl.replace("\n", eol).encode("utf-8"), 1)
    assert expected == cur, f"FAIL {path}: bytes differ"
    print(f"PASS {path}")
```

## Pitfalls hit (all real)

- **`file` reports "with CRLF, LF line terminators"** = MIXED file
  (automation-core contract: 290 CRLF + 315 LF, 25 LF-only lines). Binary
  replace only the anchor bytes; never decode/re-encode whole file.
- **Anchor double-count**: summing CRLF-variant + LF-variant counts of a
  single-line anchor counts it twice (identical bytes). Count with the file's
  actual EOL only.
- **Anchor uniqueness**: count==1 assertion before every replace; if 2, lengthen
  the anchor (e.g. include the next line / full bullet) until unique.
- **`search_files` path mangling** on Taadaa paths — use `terminal` + `rg -n` or
  `read_file` instead (see main SKILL.md).
- **`python /c/Users/...` from git-bash** → mangled to `D:\c\Users\...`; use
  `python "C:/Users/..."`.
- **Concurrent sessions** dirty the same repos: baseline `git diff --stat`
  numbers for untouchable files must be identical after your work (proves you
  didn't disturb them). New untracked files in a repo you didn't touch =
  another session; check `git status --short` diff vs baseline.
- **Validator findings ≠ your fault**: `check_ui_compatibility.py` flags
  `agents_missing_canonical_binding` / `agents_missing_registry_binding` for any
  consumer AGENTS.md lacking the strings `ui-compatibility-contract.md` / its
  registry filename. If the flagged file wasn't in scope OR the pre-edit backup
  lacks the binding too, it's pre-existing — report, don't fix out-of-scope.

## Validator semantics (automation-core/tools/check_ui_compatibility.py)

- `CONSUMERS` list = 9 Taadaa consumer dirs; `CANONICAL_NAME =
  "ui-compatibility-contract.md"`; each consumer's registry defaults to
  `docs/ui-compatibility.md` except Tiktok-video (`docs/tiktok-ui-compatibility.md`).
- Checks per consumer: AGENTS.md contains canonical name (casefold) + registry
  filename; registry contains canonical name + all 9 REQUIRED_CONCEPTS markers
  (id/owner, ui signature, evidence, fallback order, safety bounds, verification,
  regression tests, preserved branches, affected consumers).
- Run: `cd /d/Taadaa/automation-core && python tools/check_ui_compatibility.py
  --workspace-root "D:\Taadaa"` — findings are `key: path` lines, exit 1 if any.
