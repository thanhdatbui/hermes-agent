# Stale-Read Collision: dump_selectors case (2026-08-12)

## Scenario

Task: create `tools/dump_selectors.py` in `D:\taadaa\tiktok-follow` implementing existing
tests at `follow_runner/tests/test_dump_selectors.py`. Strict single-file scope; a
concurrent writer was active in the same repo (7+ foreign dirty files, live worker PID).

## Timeline (mtime evidence, all +0700 local)

- 05:55:38 — test file v1 written (133 lines; asserted `assert not out_dir.exists()`).
- 06:03:31Z baseline snapshot: `tools/dump_selectors.py` did NOT exist (`stat` error),
  focused pytest → 3 failed with `FileNotFoundError` (canonical RED).
- 06:05:58 — foreign writer REWRITES the test file (v2, 147 lines; asserts
  `out_dir.is_dir()` + `list(out_dir.iterdir()) == []` — semantics inverted).
- 06:08:32 — foreign writer creates `tools/dump_selectors.py` (292 lines, LF, read-only
  probe matching the v2 contract).
- 06:12 — writer's python process still alive (PID 14957); pyc compiled.

## The trap

1. I read the test file EARLY (v1, 133 lines) and designed the production contract from it.
2. Mid-session, pytest on the SAME path reported **3 passed** — contradicting my analysis
   that the missing-file state should fail / that test 2 semantics were inverted.
3. A byte-identical out-of-repo replication of the recorded test ALSO failed on
   `assert not out_dir.exists()` — matching my stale read, NOT the live suite.
4. Re-reading the test file on disk revealed 147 lines: the assertion had been flipped
   (`is_dir()` instead of `not exists()`) and `read_text` vs `read_bytes` changed.

Root cause: the suite executed live disk; my snapshot and replication described the
superseded v1. Not a probe bug, not a product bug — a ghost-version read.

## Resolution

- Re-stat + re-read scoped files in the SAME evidence window before any conclusion.
- Because foreign work was COMPLETE (file exists, tests pass, py_compile OK,
  `git diff --check` clean, LF EOL, no trailing whitespace), the correct move was
  pivot-to-verification, NOT re-implementation: no write, no commit, no clobber.
- Reported honestly: "implemented by concurrent writer (mtimes 06:05:58/06:08:32),
  verified by me" — never claim authorship of foreign bytes.

## Windows runner traps hit

- git-bash `$TEMP` → `/tmp` (MSYS) is unresolvable by native Windows pytest:
  `file or directory not found: /tmp/...`, `collected 0 items`, `no tests ran in 0.00s`,
  exit 4. Use a Windows-visible temp path for any out-of-repo pytest replication file.
- `git diff --check` is vacuous for UNTRACKED files — check EOL/trailing whitespace
  manually (python one-liner counting CRLF + trailing ` ` / `\t` per line).

## Evidence checklist that closed the task

- RED: baseline run at 06:03:31Z (3 failed, FileNotFoundError) — pre-existing, mine.
- GREEN (foreign): `PYTHONPATH="D:/Taadaa/automation-core/src;." python -m pytest
  follow_runner/tests/test_dump_selectors.py -q -p no:cacheprovider` → `3 passed`.
- `python -m py_compile tools/dump_selectors.py` → OK.
- `git diff --check` → exit 0 (only pre-existing autocrlf warnings on OTHER files).
- Untracked-file EOL/whitespace check → LF, zero trailing-whitespace lines.
- Repo untouched by probe artifacts (tests use tmp_path); temp replication file deleted.