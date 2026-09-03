# AG Opus exact-byte audit — invocation & guarded commit (Phase 9B.x)

Concrete mechanics for the independent audit gate. The philosophy lives in
`exact-byte-audit-and-fixture-lessons.md`; this file is the *how-to run it*.

## Run the auditor

### Pre-commit (PREFERRED for uncommitted allowlist)
The auditor posts the full prompt to the 9router chat endpoint and parses
`AG_AUDIT_VERDICT=` from the response.

```
# NINEROUTER_API_KEY must be set in the environment (check: if [ -n "$NINEROUTER_API_KEY" ])
/d/Taadaa/python-envs/automation/Scripts/python.exe \
  D:/Taadaa/reports/ag-audit/ag_audit_direct.py \
  <prompt.txt> ag/claude-opus-4-6-thinking <response.md> 600
```

- `ag_audit_direct.py` signature: `(PROMPT_FILE, MODEL, OUT, TIMEOUT)`.
- **Model string MUST be `ag/claude-opus-4-6-thinking`** (the `ag/` provider
  routes to Claude Opus). Do NOT pass `C:` or a bare model name — a 9A.5 bug
  fed the path as the model and got a 404.
- A local 9router must be up (the same endpoint the coordinator already uses).
  `/v1/models` may not be implemented; chat/completions is what works. If the
  call errors with connection-refused, the router is down.
- Long call: run in background (`background=true`, `notify_on_complete=true`),
  `wait` up to 500s. Foreground timeout caps at 600s — split the quick builder
  (foreground) from the audit (background) so you never exceed it.

### Post-commit alternative
`bash D:/Taadaa/reports/ag-audit/run-ag-audit.sh <repo-path> <commit> [model] [timeout]`
(stages the diff via `git show <commit>`). Use when the candidate is already committed.

### DEPRECATED — do NOT use
`D:\Taadaa\tools\invoke-ag-audit.ps1` is the old launcher. The official
auditor is `run-ag-audit.sh` / `ag_audit_direct.py`. Do not route through the
PS1.

## Build the audit bundle (build_phase9_9bN_reaudit.py pattern)

1. Assert `git rev-parse HEAD` == expected baseline; assert branch.
2. Compute `sha256(plan.md)` and embed it (auditor checks against the approved plan).
3. For each allowlist file: embed SHA-256, byte count, LF count, CRLF count,
   BOM flag, and the FULL bytes (line-numbered) — untracked files included.
4. Embed the relevant plan contract section (e.g. `numbered(PLAN, 906, 994)`),
   the worker/evidence JSON (self-report — challenge independently), and the
   exact `git status --short` output.
5. Prompt demands the first non-empty line be exactly `APPROVED` / `MINOR_FIXES`
   / `REJECT`, then locator-based findings only.
6. Write prompt to an absolute path, then run `ag_audit_direct.py`.

## Guarded commit helper (commit_phase9_9bN.py) — checklist

Run ONLY after the response's first line == `APPROVED`:
1. Read PROMPT + RESPONSE; first non-blank response line == `APPROVED` else die.
2. `git rev-parse HEAD` == EXPECTED_PARENT else die.
3. `git status --porcelain -z --untracked-files=all` paths == exact allowlist
   (no more, no fewer) else die.
4. `git diff --check` clean else die.
5. For each allowlist file: prompt-embedded SHA-256 == current file SHA-256
   (candidate must not have changed since the audit) else die.
6. EOL/BOM gate: no BOM, no `\r\n` in any allowlist file.
7. `git add -- <allowlist>`; `git diff --cached --name-only` == allowlist;
   `git show :<file>` staged-blob SHA-256 == current file SHA-256.
8. `git commit -m <msg> -- <allowlist>` (no amend, no push).
9. `git rev-parse HEAD^` == EXPECTED_PARENT; committed files == allowlist;
   worktree clean after commit.
Write the verdict/state JSON to
`C:\Users\Kibe\AppData\Local\hermes\cache\terminal\phase9-9bN-commit-result.json`.

## MSYS / Windows path pitfall (lost a handoff once)

Python-on-Windows invoked from the MSYS/git-bash terminal does NOT understand
paths like `/c/Users/Kibe/...`. It treats them as relative to the current
drive: when the shell cwd is on **D:**, `Path('/c/Users/Kibe/x.json').write_text(...)`
actually writes to `D:\c\Users\Kibe\x.json`. The file "disappears" — the next
step that reads `C:\Users\Kibe\x.json` finds nothing and dies.

**Rule:** always pass Windows-style drive-letter paths to Python code run from
the MSYS terminal: `C:/Users/Kibe/...` (forward-slashes with the drive letter)
or `C:\\Users\\Kibe\\...`. The MSYS `/c/...` form only works reliably when the
cwd happens to be on C:. Never rely on it for files the audit/commit pipeline
must later re-read.

## Audit-gate lessons (9B.3/9B.4, 2026-08-14)

- **The AG auditor is cheap, not quota-eating.** Each audit = 1 prompt
  (~23–210 KB, avg 35–60 KB for 9B) + 1 response (~5–15 KB) ≈ 15–25k tokens,
  ONE call, no loop, no tools — vs the coordinator loop at 30–60k tokens/turn
  over dozens of turns. Audit is ~1–3% of the worker cost; it routes via the
  `ag/` provider (separate credential) so it does not burn the main model's
  quota. Frequency = 1 per task (+1 if a minor fix re-audits), not spam.
- **Auditor catches dead-path defects in PS1 wrappers.** When the PS1 passed
  `$env:HERMES_CRON_STAGING_PREFLIGHT` to Python but never set it, AG flagged
  it as a dead-path bug. The fix: the PS1 computes the preflight verdict itself
  and sets the env from that value. After ANY post-approval edit, rebuild the
  bundle (recompute hashes) and re-audit so committed == audited.
- **Re-audit after folding in leftover WIP.** If an uncommitted working-tree
  change from a prior task turns up (e.g. a deterministic-clock test fix), fold
  it into the allowlist, extend the bundle, and re-audit the enlarged set —
  never leave it uncommitted or commit it un-audited.
- **Ground the CLI contract before writing argv builders.** Re-probe
  `hermes cron create/pause/edit --help` and `list --all` (human, no `--json`)
  in the same session. `hermes cron update` does not exist — the negative guard
  is the only place that name may appear (in `reject_update`).
- **Fake job ids MUST be hex.** The human-list parser regex is
  `[0-9a-fA-F]{4,}`; a fake id like `j0001` parses to `[]` and trips the
  human/canonical drift check. Use `0001abcd`-style ids in fakes.
- **`str(timedelta(hours=7))` is `"7:00:00"`, not `"+07:00"`.** Assert
  `resolved_offset` is truthy (or compare via `hcm_equivalent`), never string-equal
  to `"+07:00"`.