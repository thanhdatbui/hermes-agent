# Context-Bloat Scan Reference

Use this after HANDOFF normalization or when a repo feels slow/heavy to load. This is an inventory aid, not a deletion script.

## Classification

| Class | Typical files | Action |
|---|---|---|
| Startup policy | root/repo `AGENTS.md`, `CLAUDE.md`, `PROJECT_RULES.md`, `HANDOFF.md` | Measure first; trim stale history or split active policy from archive only with proof |
| Task-gated source/docs | large `.py`, `.md`, `.json`, workflow/test files | Keep intact; read by task scope, consider module/reference split only when justified |
| Runtime/generated/vendor/data | logs, JSONL ledgers, screenshots, decrypted exports, builds, lockfiles, binaries, backups | Check tracked/ignored status and loader references; do not load whole files by default |

## Required evidence per candidate

Record:

- absolute/ repo-relative path;
- byte size and line count;
- tracked, ignored, or untracked status (run Git from the candidate repo, not the workspace root);
- whether `AGENTS.md`, `PROJECT_RULES.md`, a loader, or a task explicitly requires reading it;
- sensitive-data risk (credentials, OTP, account/workbook rows, sessions, decrypted workflows);
- active-work status / skip reason;
- recommended action: keep, bounded-read rule, archive/reference split, ignore, or later refactor.

## Priority rules

1. A large always-loaded policy file outranks a larger binary or vendor asset for model-context investigation.
2. A large HANDOFF in an active repo is inventoried but not edited; state the deferral explicitly.
3. Runtime logs and JSONL are context risks only when a rule or workflow reads them wholesale. Prefer tail/offset/filter queries and summaries.
4. Tracked sensitive/generated files are a governance risk even if they are not startup-loaded; flag them separately from pure context bloat.
5. Do not delete or rewrite a file solely because it is large. Confirm its loader/consumer and preserve a backup or Git path before any edit.

## Minimal scan workflow

1. Inventory root and repo startup docs and compute bytes/lines.
2. Scan non-binary files above a threshold (suggested 100–250 KiB) and classify by the table above.
3. For the top candidates, check Git tracking/ignore state inside the owning repo.
4. Search startup docs for `read`, `load`, `full`, `entire`, `history`, `logs`, and referenced paths.
5. Report P0/P1/P2 with evidence and explicit deferred/active scopes.
6. Only then propose edits; keep the scan read-only unless the user separately authorizes cleanup.

## Known fleet pitfalls

- `Tiktok_Reg` may be under active work; do not trim or inspect-write its HANDOFF without an explicit scope change.
- A `.git` file containing `gitdir: ...` is a valid Git worktree/pointer; test `git rev-parse --git-dir` rather than `os.path.isdir('.git')`.
- A large file can be tracked, ignored, or untracked; workspace-root Git commands can give false "not a repo" results for child repos.
- Root `AGENTS.md` historical/deprecated blocks may be removable from startup only after an active-policy comparison; do not assume headings marked historical are safe to delete without checking references.
- Keep scans/reporting Vietnamese and concise when the user prefers operational output.
