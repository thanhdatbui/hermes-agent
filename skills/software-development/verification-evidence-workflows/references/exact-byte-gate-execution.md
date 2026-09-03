# Exact-byte gate execution (Phase 9 style: audit → allowlist commit)

Reusable mechanics for gated tasks that require AG Opus exact-byte approval and
an exact-allowlist commit before the next task starts. NO-LIVE throughout.

## 1. Delegate-crash fallback (learned 2026-08, 3/3 failures)

`delegate_task` background workers for large repo-implementation tasks on this
machine repeatedly end with `API call failed after 8 retries: cannot convert
float infinity to integer`. The worker reports `completed` but **lands zero
files** — its isolated terminal session (and everything written there) is lost.

- Do NOT re-delegate on the same task after one such crash. Fallback that
  worked: **implement directly in the main session** (terminal is persistent,
  files land on disk reliably).
- If you must delegate: brief must demand `land-files-first` (verify each file
  exists + `git status` after writing) and a **string-only** handoff JSON
  (no float/duration fields — they trigger the crash).
- Handoff JSON: write to the correct Windows path `C:/Users/...`; in git-bash,
  `Path('/c/Users/...')` under Windows Python resolves to the current drive
  (`D:\c\Users\...` when cwd is on D:) — always use the drive-letter form.

## 2. AG Opus exact-byte audit (pre-commit)

- `D:\Taadaa\tools\invoke-ag-audit.ps1` is DEPRECATED (PS 5.1 hang).
- `D:\Taadaa\reports\ag-audit\run-ag-audit.sh <repo> <commit> [model] [timeout]`
  audits a COMMIT via `git show` (post-commit only).
- **Pre-commit audit:** call the direct runner:
  `python D:/Taadaa/reports/ag-audit/ag_audit_direct.py <prompt-file> ag/claude-opus-4-6-thinking <response-out> 600`
  (needs `NINEROUTER_API_KEY`; posts to `http://127.0.0.1:20128/v1/chat/completions`).
  Prints `AG_AUDIT_VERDICT=APPROVED|MINOR_FIXES|REJECT|UNPARSEABLE`; the
  response body (first non-empty line = verdict) is written to `<response-out>`.
- Bundle builder pattern (`build_phase9_9bX_reaudit.py`): assert
  `EXPECTED_HEAD` + plan SHA, snapshot exact `git status`, per-file bindings
  `sha256/bytes/lines/lf/crlf/bom`, embed plan section + worker evidence +
  full file bodies, and a fixed set of mandatory re-audit questions (one per
  contract bullet) + verdict rule. Write the prompt with `newline="\n"`.
- Re-run the builder + audit after ANY candidate change; only pre-commit exact
  bytes count. Green tests are evidence, never approval.

## 3. Exact-allowlist commit helper (`commit_phase9_9bX.py`)

Guard rails before `git commit`:
- Verdict first line must be exactly `APPROVED`, else abort.
- Pre-commit HEAD == expected parent; branch == expected; dirty paths ==
  allowlist exactly (no extra modified files, no WIP).
- Audit-prompt hashes == current working-tree hashes (no post-audit drift).
- EOL/BOM gate: no CRLF bytes, no UTF-8 BOM.
- `git add -- <allowlist>`; staged names == allowlist; staged-blob SHA-256 ==
  working hash; then commit `-- <allowlist>`; verify post-commit parent,
  committed files, clean status. Never push/amend.
- If an unrelated file is dirty (e.g. a flaky-test fix in a previously committed
  file), fold it into the audit bundle as an extra allowlisted path rather than
  leaving WIP, or commit it separately — never commit with the helper while the
  worktree has un-audited dirty files.

## 4. Windows pytest spawn pitfalls

- A `.py` cannot be `subprocess`-exec'd as `argv[0]` on Windows
  (`OSError: [WinError 193] %1 is not a valid Win32 application`). Use a
  `.cmd` shim that re-execs the real python to record argv/cwd/env:
  `python -c "import json,os,sys; ..." "%~f0" %*`.
- A fully stripped child env breaks child startup on Windows: forward
  non-secret infra vars `SystemRoot, SystemDrive, ComSpec, PATHEXT, TEMP, TMP`
  (case-insensitive on Windows) plus a sanitized `PATH`.
- `git diff --check` may warn "LF will be replaced by CRLF" — benign when the
  file bytes contain no `\r\n` (verify with `grep -c $'\r'`).
- SUT with time-window logic (e.g. wrapper silent 02:00–05:59 HCM): tests must
  inject a fixed clock (env override like `HERMES_CRON_NOW`); a real-now test
  is time-of-day flaky and will fail whenever the suite runs inside the
  window.
