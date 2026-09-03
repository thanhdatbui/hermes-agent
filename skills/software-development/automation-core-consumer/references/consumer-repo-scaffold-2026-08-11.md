# Consumer repo scaffold from scratch (proven 2026-08-11, tiktok-follow)

Goal: create a NEW consumer repo under `D:\Taadaa\<name>` that matches sibling
repos (`tiktok-luot nuoi acc`, `tiktok-log-in`, `Tiktok_Reg`, `Tiktok-video`).

## Recipe

1. **Template source**: pick the closest-purpose sibling and copy
   `AGENTS.md`, `PROJECT_RULES.md`, `CLAUDE.md`, `.gitignore` from it. The
   rule files are ~90% shared cross-repo contract (worker policy, recovery
   contract, audit routing, quota gate, commit gate, RULE 3 BƯỚC) — only a
   handful of strings are repo-specific.
2. **Init**: `mkdir <name> && cd <name> && git init -b master` — siblings use
   `master`, NOT `main` (git 2.54 on this host supports `-b`).
3. **Folder skeleton** (each dir needs `.gitkeep` except runtime/):
   ```
   .agents/ .hermes/plans/ config/ data/ docs/ai/ reports/ scripts/
   tasks/ tests/ tools/ runs/
   <purpose>_runner/{config,core,flows,runs,tests,tools}
   ```
   Runner dir is `<purpose>_runner/` (e.g. `login_runner`, `follow_runner`),
   NOT `python_runner` — that name is only used when the purpose is generic.
4. **Adapt copied files** via ONE python replace-script (write_file, run with
   Windows path; `io.open(newline='')` preserves CRLF; count-assert every
   anchor `== 1` before replace — same discipline as docs-rule edits). Typical
   replacements:
   - AGENTS.md: `# <Old> Agent Instructions` title, dev-guide path
     `docs/ai/<old>-development-guide.md` → `docs/ai/<name>-development-guide.md`,
     `<old-purpose> scheduler/policy` → `<new-purpose>`.
   - PROJECT_RULES.md: "Project-specific guardrails for `<old>`" line, Scope
     paragraph, `<old>-session` runner names in PITFALLs, derived-file examples.
   - CLAUDE.md: `# <old>` → `# <name>`.
   - .gitignore: `python_runner/...` → `<purpose>_runner/...`.
   Verify with `grep -rn "<old>\|nurture\|python_runner" <files>` → nothing.
5. **Write fresh files**: `HANDOFF.md` (state + next steps + ops notes in
   Vietnamese), `PROJECT_STRUCTURE.md`, `CHANGELOG.md` (initial entry),
   `README.md` (quick conventions: ADB path, workbook path, lock dir),
   `docs/ui-compatibility.md` (registry skeleton with the 9-concept contract
   template — required by the Shared UI Compatibility Binding),
   `docs/ai/<name>-development-guide.md` (condensed recovery/device/lock/
   workbook contract), `requirements-automation-core.txt`.
6. **Pin the wheel**: `ls D:/Taadaa/automation-core/dist/*.whl | tail -1`
   → `automation-core @ file:///D:/Taadaa/automation-core/dist/automation_core-<ver>-py3-none-any.whl`
   with the "# Upgrade only between runs after the shared wheel has been
   validated." header.
7. **Commit + remote**: `git add -A && git commit -m "chore: scaffold ..."`,
   then `gh repo create <owner>/<name> --private --source=. --push`
   (siblings are PRIVATE; `--source=.` uses the local repo, no empty remote
   repo needed). Push sets up `master` tracking automatically.

## Pitfalls

- **Unanchored `runs/` in .gitignore matches at ANY depth.** Template
  `.gitignore` line `runs/` silently swallowed BOTH `<purpose>_runner/runs/.gitkeep`
  AND top-level `runs/.gitkeep` (git check-ignore -v showed the match). A
  directory-level exclude cannot be re-included by `!<path>/.gitkeep`.
  Fix: replace bare `runs/` with `/runs/*` + `!/runs/.gitkeep` (ignore
  contents, keep the dir). `runtime/` stays fully ignored → do NOT add
  runtime/.gitkeep.
- **Verify ignores with `git check-ignore -v <path>`**: exit 1 = NOT ignored
  (what you want for .gitkeep files); exit 0 = ignored, and the output shows
  the exact .gitignore line responsible.
- **UI-compat validator is hardcoded**: `automation-core/tools/check_ui_compatibility.py`
  iterates a static `CONSUMERS` tuple — a new repo does NOT break the
  "OK: 9/9 consumers" check and is not auto-discovered. Add the repo to
  `CONSUMERS` only when it has real UI-compat records. AGENTS.md must still
  contain both `ui-compatibility-contract.md` and the local registry filename
  (verify: `grep -c` both → 1 each).
- **Fresh rule files keep CRLF** (copied from CRLF template); new .md files
  written via write_file are LF — git warns "LF will be replaced by CRLF" on
  add; harmless (core.autocrlf=true), same as siblings.
