# Worked example — authoring a 9-consumer recovery-adapter migration plan (PLAN-ONLY)

Session 2026-08-12. Task: write ONLY `D:\Taadaa\automation-core\.hermes\plans\2026-08-12_consumer-recovery-adapter-migration.md` (exact filename mandated); no source/test/config/consumer edits, no commit, no live/ADB/credential/workbook/log access. Deliverable verified: 490 lines, 63,421 bytes, SHA-256 `b37df0ccea2d7c5208f5fc1ddcb5387866533581eaf5a5dc52d973f230132349`, 12 phases, 9/9 consumer matrix, `git status` = 2 untracked plan files only (the new one + a pre-existing plan), 0 tracked modified, no commit.

## Governance chain actually read (order matters)

1. `D:\Taadaa\AGENTS.md` — audit ladder & one-slot rule, `SUBAGENT_RUNTIME_UNAVAILABLE` semantics, worker = fresh session-model flash/Luna/high, Terra/Sol read-only, fail-closed hard stop `AUDIT_ALL_ROUTES_FAILED`, finding classification `CONFIRMED_P0/P1 / NEEDS_PROOF / NOTE / DISPROVED`, circuit breaker (2 cycles same invariant ⇒ design audit), blind final audit.
2. `automation-core\AGENTS.md` — absolute `pm clear` ban, recovery contract state machine `DETECTED → CLASSIFIED → RECOVERY_RESERVED → RECOVERING → RECAPTURED → RETRYING → VERIFIED_SUCCESS | FINAL_BLOCKED`, cap default detection+7 live runs (consumer may tighten, never weaken/reset), device-lock ownership contract (`SAME_PROJECT_RECOVERY` / `FULL_SCOPE_TAKEOVER`), COMMIT GATE (commit only when full test suite green; fix-sai → revert immediately).
3. `docs/ai/automation-core-development-guide.md` — core app-neutral, one owner + dedicated branch/worktree, never edit core from consumer task, production must use built versioned artifact, editable-install hazard, no live validation with real ADB/accounts.
4. `docs/scope.md` — the authoritative 9-consumer list: `add mail khoi phuc`, `gan-proxy`, `Hotmail`, `register gmail`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `tiktok-log-in`, `tiktok-luot nuoi acc`, `Tiktok-video`; per-consumer PENDING evidence checklist.
5. Prior report: `docs/ai/recovery-failure-class-audit-2026-08-11.md` (Phase 4) — 9/9 PENDING, 0 consumers import `automation_core.recovery`/`escalation`, taxonomy gap, per-consumer symbol FACT tables. It was the ground-truth source for symbols; I still re-read a handful of snippets (see below) to confirm before citing path:line.

## Baseline verification commands used (git-bash on Windows)

```bash
git status --short --untracked-files=all
git rev-parse HEAD            # 8a3ede57199f2b879ea3d098ac714300b2a2f7aa
git log --oneline -16
git tag --sort=-creatordate | head -12
ls dist/ | tail -14           # wheels 0.4.36..0.4.44 — name-only, no contents read
for d in 'add mail khoi phuc' 'gan-proxy' ... ; do
  git -C "D:/Taadaa/$d" rev-parse --short HEAD
  git -C "D:/Taadaa/$d" status --short --untracked-files=all | awk 'NR<=8{print} NR==9{print "..."}'
done
```

Notable: `search_files` (ripgrep) failed with `IO error ... os error 3` on `D:\Taadaa\add mail khoi phuc` (spaces + drive letter) — consistent with the umbrella's existing pitfall. Plain `read_file` on the same paths worked fine. For multi-consumer status, `git -C "D:/Taadaa/<name>"` with POSIX-style quoting worked in git-bash.

## Per-consumer grounding pattern (FACT table)

For each of 9 consumers I recorded: repo path, HEAD short hash, current pin (read `requirements-automation-core.txt` line 2, plus `pyproject.toml` for Hotmail where the pin appears in BOTH places), key symbols with path:line verified by direct read_file snippets (not just copied from the Phase 4 report), migration state (PENDING), existing test files (FACT paths, not run), dirty-state snapshot. Findings that changed plan design:

- **Feed `tiktok-luot nuoi acc` pinned 0.4.18** — BELOW the audited 0.4.25 baseline and below the 0.4.24 lock-ownership rollout; its `RecoveryHandlerRegistry` import only exists in the scheduler/supervisor gate, NOT the feed-session runtime path → chosen as PILOT (most code evidence, registry already exists) but its phase mandates a discovery step to find the real call-site or stop with NEEDS_PROOF.
- **Pin matrix:** 0.4.18 (feed), 0.4.24 x4 (add-mail, register-gmail, f2a, login), 0.4.30 (Tiktok_Reg), 0.4.31 (Hotmail, two pin locations), 0.4.35 (video), 0.4.43 (gan-proxy) → plan targets one wheel 0.4.45 after a Phase 0 build/verify step.
- **`Tiktok_Reg`** has a `_require_runtime_core_version` gate with `REQUIRED_CORE_VERSION = "0.4.43"` in its recovery runner — pin migration must respect/update that gate, a per-consumer nuance a generic plan would miss.
- **`tiktok-log-in` "guided recovery"** appears in AGENTS/docs but has NO code symbol → labeled NEEDS_PROOF with a discovery-or-stop rule (no fabricated hook point).
- Dirty states were substantial (e.g. Tiktok_Reg ~61 modified entries + 6 permission-denied `.pytest-basetemp-*` dirs; Hotmail untracked `.online_serials.txt` — a FORBIDDEN file, recorded as path+status only). Preflight snapshot + worktree-only execution is the plan's protection against overwriting them.

## Plan skeleton delivered (the 11 user requirements decoded)

1. Invariants table I1–I13 (I1 core app-neutral … I13 facts vs assumptions vs NEEDS_PROOF), each with a "hệ quả trong plan" column.
2. Topology migration section: core stays interface-only (optional `adapters.py` Protocol — decision deferred to Phase 0 gate); per-consumer adapter owns mapping, registers strict `RecoveryHandlerSpec` + `EscalationHook`; taxonomy map table (local signature → core failure class, one class per signature, un-backed classes → NEEDS_PROOF); invoke real runtime path; preserve existing flow until verifier gate; no second scheduler/retry loop (I11).
3. Sequential phases P0 → P1 (pilot) → P2…P9 → P10, one worker/worktree ownership each, no parallel same-component. Each phase: files allowlist, forbidden paths, RED tests (behavioral descriptions), GREEN guidance, verify commands with `PYTHONPATH=src` (never installed site-packages), expected evidence, commit message, independent AG Opus audit gate, rollback.
4. Per-consumer rows in §4.2 (path/symbols/pin/insertion point/mapping/budget/recapture-verifier/lock seams/tests) + §8 mapping table + §9 pin matrix (current → target 0.4.45, conditions).
5. Facts vs assumptions vs NEEDS_PROOF explicitly labeled throughout; consumer without verified call-site → dedicated discovery phase.
6. Core distribution: bump 0.4.44→0.4.45, build wheel, verify by extracting the wheel and running smoke with `PYTHONPATH=<extract-dir>`; assert `automation_core.__file__` NOT in site-packages (the Phase 4 report documented the exact env-resolver blocker); consumer pins updated only after wheel + focused tests + audit gate.
7. Preflight: per-phase snapshot of consumer dirty state, dedicated worktree/branch from clean base, preserve unrelated dirt, no forbidden reads, no live, commit gate + audit gate.
8. Shared test matrix T1–T14 (no-hook, missing/incomplete handler, HARD_STOP, NON_RETRYABLE, generic exception, budget exhausted, verifier failure, lock retained, restart/re-fire, redaction, no implicit recovery, no `pm clear` scan, no second control plane) + per-consumer existing suites referenced by path.
9. Stop conditions: NEEDS_PROOF ⇒ stop that consumer (no fake green); discovery without call-site ⇒ stop; 2 audit cycles same invariant ⇒ consolidated design audit; NEEDS_PROOF disposition required before final acceptance.
10. Per-phase allowlist/forbidden/RED-GREEN/evidence/commit/audit/rollback (satisfied by the phase template).
11. Final acceptance (P10): all 9 adapters registered + runtime-connected, pins consistent, focused tests, full core+consumer gates, no dirty file overwritten, final report.

## Final verification + report (user-mandated, verbatim shape)

```bash
F="D:/Taadaa/automation-core/.hermes/plans/2026-08-12_consumer-recovery-adapter-migration.md"
wc -l < "$F"        # 490
sha256sum "$F"      # b37df0ccea2d7c5208f5fc1ddcb5387866533581eaf5a5dc52d973f230132349
git status --short --untracked-files=all   # ONLY the 2 plan files untracked; 0 tracked modified
```

Reply format accepted by the user: absolute path, line count, SHA256, phase count, consumer-matrix count, plus a grounded summary proving every cited symbol was read (not copied) and every forbidden path was only recorded by path. Ending "Issues: không có" plus the outstanding NEEDS_PROOF items that must be dispositioned before final acceptance.

## Reusable observations

- The user's PLAN-ONLY tasks in Taadaa consistently demand: exact plan filename, no-side-effects proof via `git status`, hash + line count + counts in the reply, and strict separation of what was READ vs ASSUMED vs UNPROVEN. Deliver the verification evidence in the reply itself (commands + outputs), not just a summary of the plan's content.
- `docs/` reports from earlier phases are the cheapest safe ground-truth, but spot-check 1–3 symbols per consumer by direct read before citing them — the report itself may warn its conclusions are static-code-only.
- When a consumer pin is BELOW the module that shipped later (e.g. wheel lacks `escalation.py`), the plan must order core wheel rebuild BEFORE any consumer pin bump and prove the wheel's contents by extraction, not by trusting `dist/` names.