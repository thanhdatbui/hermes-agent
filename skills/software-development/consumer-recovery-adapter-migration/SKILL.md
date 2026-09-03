---
name: consumer-recovery-adapter-migration
description: Execute phases of the multi-consumer recovery-adapter migration (discovery + baseline-only, later RED→GREEN implementation) inside isolated worktrees without touching dirty origin repos; produce verdict-gated discovery reports with FACT/ASSUMPTION classification.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [recovery-adapter, migration, worktree, baseline, discovery, verdict, tiktok, taadaa]
    related_skills: [project-handoff-audit, git-worktree-merge-reconciliation, concurrent-workspace-safety, implementation-plan-maintenance]
---

# Consumer Recovery-Adapter Migration Phases

## When to Use

The Taadaa `2026-08-12_consumer-recovery-adapter-migration` plan (`.hermes/plans/...` under `D:\Taadaa\automation-core`) migrates recovery-adapter behavior across multiple consumer repos (P1 `tiktok-luot nuoi acc`, P2 `tiktok-log-in`, ...). Each phase runs as **discovery + baseline-only** (worker scope = report + evidence, NO patches) or **implementation** (RED tests → GREEN → verify → commit/audit gates). Use this skill whenever the user names a phase (P1/P2/P3…) or asks for "discovery + baseline-only" scope on one of these consumers.

Program state (2026-08-12): P1 feed discovery → READY_FOR_P1_IMPLEMENTATION; P2 login discovery → READY_FOR_P2_IMPLEMENTATION. Details: `references/program-state.md`.

## Core Invariants

1. **Origin repo dirty = read-only.** Never reset/clean/stage/checkout the origin worktree. Only read-only git (`rev-parse`, `branch`, `status`, `ls-files`, `ls-tree`, `grep`, `worktree list`). `git worktree add` writes only `.git/worktrees/` metadata — that is the one allowed write.
2. **Dedicated worktree from the exact base SHA**, branch named `recovery-adapter/<consumer>-p<phase>-<kind>` (e.g. `recovery-adapter/login-p2-discovery`). Worktree must be clean from HEAD at creation and stay clean except the allowed report file.
3. **Baseline before any write.** Run the exact suite the plan names from the worktree root with `python -B -m pytest -q -p no:cacheprovider` (`-B` prevents `__pycache__`). Record exit code, pass/fail, and classify EVERY failure as pre-existing (environment/sibling-project) vs real. The baseline IS the comparison reference for later GREEN claims.
4. **Read only the clean worktree copies** of files that are dirty in origin (they exist at HEAD in the worktree). Never open the origin's dirty versions.
5. **Forbidden file classes**: dirty files outside the plan allowlist, credentials/workbooks/logs/raw artifacts/.env/session/generated runtime. Enumerate forbidden paths from `git status --short` (path/status only) and never open their contents.
6. **No live side effects** in discovery: no ADB/device/TikTok/cron/subprocess runs, no `pm clear`, no installs, no dependency changes. Record interpreter + installed dep version + pin file version + target version as facts (e.g. hermes venv has automation_core 0.4.43 installed; pin file (clean HEAD) names a different wheel; target is 0.4.45).
7. **Verdict criteria**: `READY_FOR_P<n>_IMPLEMENTATION` only when a concrete offline-testable runtime seam is proven (FACT path:line + existing offline tests over that seam). Otherwise `NEEDS_PROOF` and stop. Never claim live-connected.
8. **Post-write verification**: worktree has ONLY the report untracked; worktree tracked-file manifest (`git ls-files -s`) identical pre/post; origin status manifest identical pre/post; no commit/push.

## Discovery Workflow

1. **Preflight** — record origin toplevel/HEAD/branch, worktree HEAD (must equal base), branch, and pre-existing worktrees (don't disturb them). Snapshot origin status (path/status only) into an evidence dir OUTSIDE the repo (`C:\Users\Kibe\p<n>-<consumer>-discovery-evidence-<date>\`).
2. **Docs read order** — `D:\Taadaa\AGENTS.md`, repo `AGENTS.md`, `PROJECT_RULES.md`, `HANDOFF.md`, `docs/ai/*development-guide*`, the plan's exact phase line range, and the prior phase's discovery report as the pattern doc.
3. **Baseline** — exact suite from the plan; save raw output to the evidence dir; record interpreter/pin facts (invariant 6).
4. **Discovery trace** — walk real runtime call-sites from entrypoint to the target function and terminal paths. Emit `FACT path:line` (from the CLEAN worktree file) or explicit `ASSUMPTION` / `NEEDS_PROOF`. Answer the plan's specific questions (e.g. "is X the budget-exhausted seam?", "does guided recovery exist?" — grep the whole allowlist; 0 hits = DISPROVED, not "maybe").
5. **Report** — Vietnamese, structure per `templates/discovery-report.md`. Then post-write verification (invariant 8); compute report line-count + SHA256 AFTER final edits and record them in the summary.

## Pitfalls (learned P1 → P2)

- **MSYS/bash path handling**: `git -C /d/Taadaa/...` can fail with "cannot change to" and `search_files` can IO-error on `/d/...` paths (even though the dir exists). Use Windows-style `D:/Taadaa/...` in `git -C` and terminal commands; prefer `read_file`/`write_file` with `D:\...` paths. For enumerating tracked files in a clean worktree, `git ls-tree -r --name-only HEAD` (or `git -C <wt> ls-files`) is reliable and lets you filter out forbidden files by name before reading.
- **Plan line numbers may reference the DIRTY tree** (P2 plan cited `:342`/`:117`/`:224`/`:108`; clean HEAD had `:284`/`:59`/`:166`/`:96`). Re-anchor every plan line to the clean worktree file and note the delta in the report. Test-case line references usually match because tests are less churned (P2 FINAL_BLOCKED cases `:89,237-250,621,667` matched exactly).
- **Origin status comparison false positive**: if the pre-write snapshot file has header lines (repo path/SHA/branch), compare only the status lines (` M …` / `?? …`) or capture post-write with the same header format. A naive `diff` flags a spurious change.
- **Pre-existing baseline failures are part of the baseline**: classify them (e.g. sibling `D:\Taadaa\Tiktok_Reg` missing `scripts.target_inventory` → ModuleNotFoundError in an isolated-provider import test) and state that GREEN comparisons must use this baseline, not "fully green".
- **Evidence outside repo**: baseline output, status snapshots, and tracked manifests go to `C:\Users\Kibe\p<n>-…-evidence-<date>\` — the worktree must only ever gain the report file.
- **Two runtime paths can be distinct processes**: e.g. `scheduler.py` spawns a reconcile subprocess while `cli.py --live` runs the executor in-process — verify which entrypoint the plan targets before choosing the seam.

## Implementation Phase (RED → GREEN → AG Audit loop)

When a phase moves past discovery into implementation (P1 feed GREEN at commit `2c2e21d` / fix `5b10635` / `6c52bea`, 2026-08-12):

1. **Venv must be genuinely isolated** — global `PYTHONPATH` points at the hermes venv site-packages, which shadows whatever you install. Create the venv from a REAL runtime (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe -m venv <path>` — `py -3.11` launcher has NO runtime) and prefix EVERY command with `env -u PYTHONPATH`. Verify `sys.prefix`/`sys.executable` point into the venv, `automation_core.__file__` resolves inside its site-packages, and `pip show automation-core` reports the pinned wheel version. A venv whose `python.exe` resolves back to hermes site-packages is BROKEN — rebuild, don't patch.
2. **RED → GREEN**: RED = revert seam to HEAD → collection fail with the exact ImportError proving the adapter is unwired; GREEN = re-apply → full pilot pass. Record both counts.
3. **AG audit gate on EVERY commit**: `bash /d/Taadaa/reports/ag-audit/run-ag-audit.sh "<wt>" <commit>` → verdict line `AG_AUDIT_VERDICT=...`. Loop until `APPROVED`:
   - `REJECT` → fix ALL MAJOR findings (they carry file:line locators) → new commit → re-audit. Do not re-audit the same SHA.
   - `MINOR_FIXES` → findings that say "confirm/not visible in diff" are satisfied by adding PROOF TESTS (assert the exact redaction key, assert `adapter.queue.registry is adapter.registry`, unit-test core `redact_value` on the dropped secret patterns) rather than production churn → new commit → re-audit.
   - `APPROVED` → push and proceed. See `references/implementation-phase.md` for the full audit-response patterns (REJECT M1–M3 / MINOR_FIXES F1–F3 proof-test closes), the CRLF-safe edit recipe, and the venv-isolation checklist.
4. **Test edge that fails for the wrong reason**: core `BatchRecoveryOrchestrator` with `max_meaningful_attempts=1` never reaches the durable `FAILED_LOCKED` state (attempts spent before `finalize_failed_locked`, `_lock_failed` only transitions `CLASSIFIED`). This is a pre-existing core edge BELOW the meaningful floor — fix the TEST to use `max_meaningful_attempts=2` (matches the "meaningful 8" policy), never patch core to appease it.
5. **Stale `__pycache__` makes pytest run old tests**: after editing/renaming a test (e.g. `test_mode2_missing_fails_closed` → `test_mode2_module_available_after_implementation`), pytest may execute the CACHED old test and fail with an assertion that no longer exists in source. Clear `__pycache__` (or use `-B`) and re-run before diagnosing.
6. **Drive git via Python when MSYS can't**: some worktree paths (e.g. `D:\Taadaa\tiktok-luot-nuoi-acc-recovery-adapter-p1-wt`) make `git -C /d/...` fail with "cannot change to" while `ls`/Python `os.scandir` succeed. Use `subprocess.run([...], cwd=<Windows path>)` from a small Python script for status/diff/commit/log on those paths.

## Verification Checklist (end of every phase)

- [ ] Worktree `git status --short` = only `?? docs/ai/recovery-adapter-discovery-<consumer>-<date>.md`
- [ ] Worktree tracked manifest identical pre/post
- [ ] Origin status manifest identical pre/post (or documented out-of-control change with evidence)
- [ ] Report: line count + SHA256 computed after final edits, recorded in the summary
- [ ] No commit/push/stage; EOL LF; no source/test/config/pin edits
