# Running Verification Probes on Windows git-bash (Hermes terminal)

Reusable runbook for writing and executing verification/probe scripts on this Windows
host where the `terminal` tool runs bash (MSYS/git-bash), not PowerShell.

## Golden rules

1. **Write the probe script OUTSIDE the repo** (e.g. `C:\Users\Kibe\probe.py`) via
   `write_file` — keeps the repo's `git status` clean and avoids polluting the
   deliverable. Delete it after (`rm -f 'C:/Users/Kibe/probe.py'`).
2. **One fresh `tempfile.mkdtemp()` state root PER probe.** Journal/bridge/filesystem
   share state; a later probe reusing an earlier probe's root silently replays the
   earlier journal entries and can return a misleading outcome (see case study:
   unregistered-handler probe returned HANDOFF because a prior probe's HANDOFF sat in
   the same root's journal).
3. **Prefer `write_file` + `python -B 'C:/path/probe.py'` over bash heredocs.**
   Long `python - <<'PY'` heredocs on this transport can die with
   `line N: unexpected EOF while looking for matching` for no visible reason — the
   command transport mangles quoting. write_file avoids the whole class.

## Path pitfalls (all observed this session)

- **MSYS path mangling**: with cwd on `D:\...`, an argument like `/c/Users/Kibe/probe.py`
  is converted to `D:\c\Users\Kibe\probe.py` → "can't open file". Use the native
  `'C:/Users/Kibe/probe.py'` form (single-quoted, forward slashes) instead.
- **`sys.path[0]` is the SCRIPT's directory, not the cwd.** Running
  `python C:/Users/Kibe/probe.py` from inside the repo does NOT put the repo on
  `sys.path`. Add `sys.path.insert(0, r'D:\<repo>')` at the top of the probe.
- **`Path('.')` resolves to the runner's cwd**, not the repo. Use an absolute
  `ROOT = Path(r'D:\<repo>')` in probes that load config fixtures.
- **`python -B -m py_compile <files>` still writes `.pyc` into `__pycache__`** —
  harmless if the repo gitignores it (`git check-ignore <pyc>` confirms). `-B` only
  stops import-time bytecode; explicit py_compile writes regardless.
- **`git diff --check` is vacuous for untracked files** — all files of a new package
  show as `??` and get no whitespace check. Check EOL drift manually
  (`python -c "open(r'f','rb').read().count(b'\r\n')"` vs LF count).
- **`git -C '/d/...'` and `/mnt/d/...` forms can fail** with "No such file or directory" even though the dir exists — MSYS drive-letter prefixing doesn't resolve these reliably on this host. Use the native `D:/...` form (quoted) for `git -C`, `cd`, and python path args. Also probe with `python -c "import os; os.path.exists('D:/...')"` when plain `ls` disagrees with your expectation.
- **Hermes `search_files` (ripgrep-backed) can fail on non-ASCII/space directory names** (e.g. `D:\Taadaa\tiktok-luot nuoi acc`): `Search failed: rg: ... IO error ... (os error 3)`. This is a Hermes-tool quirk, NOT a repo problem — fall back to terminal `grep -rn '<pattern>' python_runner --include='*.py' | grep -v __pycache__`, or when grep quoting gets hairy, a `python -c` loop over `Path(r'<repo>').rglob('*.py')` reading lines and filtering in Python (also yields line numbers for read_file offsets). Note the asymmetry: `write_file`/`read_file` handle the same native absolute paths fine (the plan file was written to the Vietnamese dir without issue) — only ripgrep-backed search chokes. Verify written files with terminal `ls`/`wc -l`, not search_files.

## Verification checklist after a fix (any "verify the remediation" task)

1. Replicate the ORIGINAL attack shapes (audit probe code, review findings) verbatim-ish
   against the fixed code; tabulate ACCEPTED / REJECTED per probe.
2. Run all suites: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q <4 files>`; record
   per-file counts (`--collect-only -q | awk -F'::' '{print $1}' | sort | uniq -c`).
3. `python -B -m py_compile <scoped files>`.
4. `git diff --check` + manual EOL check (untracked caveat above).
5. Confirm no new repo files from you: `git status --short --untracked-files=all` vs
   baseline; delete temp probe scripts.

## Baseline-verification discipline (collision detection)

At session start, record: `git status --short --untracked-files=all`, `stat -c '%y %n'`
for scoped files, `date`, test pass count, and read_file line counts. Before the first
write to any scoped file, re-stat and re-grep an anchor — any mtime newer than baseline
with content you didn't write means a concurrent worker owns the file (see
`concurrent-workspace-safety` SKILL.md).