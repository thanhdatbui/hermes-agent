# Worked example: MINOR_FIXES audit findings demanding new design (FAILED_LOCKED plan)

Session: PLAN-ONLY patch of `D:\Taadaa\automation-core\.hermes\plans\2026-08-11_ai-escalation-failed-locked.md`
per audit findings. Task: "Chỉ sửa plan markdown, không sửa source/test/config, không commit, không live."

## Finding archetypes → how each was mapped into the plan

| Finding | Plan sections touched (ALL of them) |
|---|---|
| MEDIUM: Phase 1 must list + test `global_recovery.py` — every `RecoveryWorkerLease` terminal-status set (`mark_terminal`, `acquire`, `watchdog_action`) must include `FAILED_LOCKED`; add watchdog test "FAILED_LOCKED không replace" | Files list, RED test R1.6, GREEN paragraph, Acceptance, Gate audit. Verify commands unchanged (file already in list). |
| MEDIUM: `scheduler/base.py` `_device_lock_available` = FAILED_LOCKED unavailable/blocked; `_terminal_result_proven` = terminal/proven; re-fire no reacquire; + regression test | Files list, RED R1.3 (rewritten), GREEN, Acceptance, Verify commands (added `tests/test_scheduler_base.py` — confirmed the file exists first via `ls tests/`). |
| MEDIUM: must NOT claim "tái sử dụng nguyên trạng `finalize_blocked`" — design separate `finalize_failed_locked` working from CLASSIFIED/RECOVERY_RESERVED/RECOVERING/RECAPTURED/GUIDED_RECOVERY_REQUIRED; update `_allowed`, `TERMINAL_REQUIRES_COMPLETION_GATE`/`RecoveryCompletionGate.verify`, `results.py::_TRANSITIONS`; keep FINAL_BLOCKED contract intact; evidence minimal redacted, missing artifact ≠ success | Files list, RED R1.7 + R1.8 (edge tests), GREEN completely rewritten, Acceptance, Gate audit. |
| MEDIUM: Phase 2 hook coverage must list `BatchRecoveryOrchestrator.preflight` (NO_HANDLER via `validate_required`), `run_all`/`_run_one` generic exceptions, HARD_STOP/NON_RETRYABLE, reserve/start/recapture/verifier failures; preflight hook must not break other targets; exception → ESCALATION_REQUIRED or FAILED_LOCKED fail-closed, no swallowed errors; + RED tests | Trigger matrix (2 new rows + rewritten rows), Files list, RED R2.9–R2.11, GREEN, Acceptance, Gate audit. Also fixed a stale downstream reference ("5 trigger class" in Phase 4 GREEN). |
| Baseline timing `1.69s` → machine-dependent | Both occurrences (mục 4 verified-state + Phase 0 verify expectation) rewritten as `timing machine-dependent — audit ghi nhận 1.43s, không coi timing là invariant`. `grep -c '1.69s'` = 0 after. |

## Key moves that worked

1. **Ground-truth every symbol the audit named BEFORE writing it into the plan.** Used terminal grep (search_files was failing) to confirm real code:
   ```bash
   cd /d/Taadaa/automation-core && grep -n 'def mark_terminal\|def acquire\|def watchdog_action' src/automation_core/global_recovery.py
   grep -n 'def _device_lock_available\|def _terminal_result_proven' src/automation_core/scheduler/base.py
   grep -n 'def finalize_blocked\|_allowed\|TERMINAL_REQUIRES_COMPLETION_GATE\|def verify' src/automation_core/recovery.py
   grep -n 'def ' src/automation_core/recovery_runner.py   # <- found run/_run_one, NO run_all
   ls tests/                                                 # confirm test files exist before naming them
   ```
   `run_all` did NOT exist — real method is `run`/`_run_one`. Plan references `run`/`_run_one` and notes `(audit gọi nhóm này là run_all)`. Also confirmed `mark_terminal` guards `status not in {...}` (line 261) and `watchdog_action` terminal-set (line 278) — the exact lines that need `FAILED_LOCKED` — so the plan text is precise about WHERE.

2. **Negate the banned approach explicitly in the plan text**, not just omit it: "KHÔNG tái sử dụng nguyên trạng `finalize_blocked` (vốn đòi attempts>=2 + state `RETRYING` + artifact bắt buộc)". After patching, `grep -n 'tái sử dụng nguyên trạng'` — the only hits must be inside the negation.

3. **Policy sentences kept verbatim.** The user's fail-closed policy lines (FAILED_LOCKED vĩnh viễn tới khi user explicit; không retry/release tự động) were left untouched; findings were added AROUND them, never replacing them.

4. **Final verification evidence reported:**
   ```bash
   wc -l .hermes/plans/2026-08-11_ai-escalation-failed-locked.md     # 270 → 280
   sha256sum .hermes/plans/2026-08-11_ai-escalation-failed-locked.md
   git status --porcelain                                            # ?? .hermes/plans/ ONLY — no repo files touched
   grep -c '1.69s' ...; grep -c '1.43s' ...; grep -c 'finalize_failed_locked' ...; grep -c 'preflight' ...
   ```
   Reported: existing path, 280 lines, SHA-256, grep counts per finding term (0 stale / ≥1 new), git status showing only the plan dir. Never reported success without the file existing — read_file is the gate.

## Anti-patterns avoided
- Rewriting plan sections the finding didn't ask to change (Phase 3/4 touched only where a finding's matrix made a reference stale).
- Referencing `tests/test_recovery_runner.py` or similar non-existent file — verified `ls tests/` first.
- Leaving the old timing `1.69s` anywhere (a machine-dependent number that would turn into a false verify failure).