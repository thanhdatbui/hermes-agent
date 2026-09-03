# AI Auto-Recovery Hard-Stop Routes (R5–R11) — implementation + verification

Reference for any task that must STOP AI auto-recovery from launching/spawning while
keeping the rest of the system alive. Captured 2026-08-22 on the Taadaa
`disable-ai-auto-recovery` plan (consumer impl worktree
`D:\Taadaa\tiktok-luot nuoi acc-implementation`, branch
`codex/disable-ai-auto-recovery-consumer`).

## Canonical constant (single source of truth)

`automation_core.global_recovery.AUTO_RECOVERY_ENABLED: bool = False`
already exists in `D:\Taadaa\automation-core\src\automation_core\global_recovery.py`.
It is `False` by construction, immutable, with NO env/flag/CLI/config override.
Every auto-recovery route consults it and returns non-success BEFORE launching/
dispatching/resuming. Re-enabling is a separate, separately-authorized release.

Import pattern (fail-closed if an older wheel lacks the constant):
```python
try:
    from automation_core.global_recovery import AUTO_RECOVERY_ENABLED
except ImportError:  # Fail closed if the canonical constant is unavailable.
    AUTO_RECOVERY_ENABLED = False
```

## Route map (where the guard goes)

| # | File | Seam | Guard placement |
|---|------|------|-----------------|
| R1 | `automation-core/.../alerts.py` | `subprocess.Popen` launcher | remove the Popen block; alert still sends (Tasks 1–2) |
| R2 | `python_runner/ai_recovery/agent.py` | `__main__` / `agent.main()` | early return before screenshot/XML/ADB/network/patch/git/resume |
| R3 | `agent.py` `_spawn_resume_process` | resume child | not invoked when disabled |
| R4 | `agent.py` `finally:` | teardown/relaunch | no relaunch / success-report / ADB/network/patch/git |
| R5 | `python_runner/scheduler/recovery_runtime.py` | `main()` / `build_parser()` / `run_target_recovery()` | BEFORE `ScheduleRecoveryRuntime` construction/activate and `run_once`/`run_incidents`/`run_target_recovery` subprocess |
| R6 | `python_runner/scheduler/recovery_supervisor.py` | `RecoverySupervisor.run()` (public) + `main()` | BEFORE `_run()` and repair/audit/live executors + resume |
| R7 | `scripts/run-schedule-recovery-watch.ps1` | `Start-Process scheduler.recovery_runtime` | + fixed `$AUTO_RECOVERY_ENABLED=$false`; `exit 0` BEFORE `Start-Process`; strips/ignores `-Dispatch`/`-EnableLiveRecovery`/`-Resume` |
| R8 | `scripts/register-scheduler-task.ps1` | recovery `Register-ScheduledTask` action | fixed `$AUTO_RECOVERY_ENABLED=$false`; override forces `$recoveryLiveArgument=''` + `$recoveryTaskEnabled=$false`; unrelated worker/tray/proxy tasks untouched |
| R9 | `scripts/hermes_cron/tiktok_runner.py` | generic `subprocess.Popen`/`run` | CLASSIFIED UNRELATED (launches `run-feed-session.ps1`/business child, no recovery dispatch). SOURCE_ONLY, no edit |
| R10 | `python_runner/hermes_cron/watcher.py` | `Watcher.process_failure()` bridge caller | BEFORE `apply_recovery`/`recapture`/`retry`/`verify` (see placement rule below) |
| R11 | `scripts/recovery-health-watch.ps1` | `Invoke-HealthCheck` `Write-ResumeRequest` + `Start-ScheduledTask` | fixed `$AUTO_RECOVERY_ENABLED=$false`; `return` BEFORE both calls |

## Guard placement rule (R10 especially)

Do NOT put the R10 guard at the very top of `process_failure()` — a top-level guard
would break the EXISTING classification/defer tests that run with `AUTO_RECOVERY_ENABLED`
globally `False` and expect `NO_HANDLER_IMPLEMENTED`/`MANUAL_REQUIRED`/defer outcomes.
Place the guard immediately before the recovery-bridge invocation (after
`claim_recovery`, before `RecoveryReservationV2.from_dict` / `apply_recovery`).
Classification paths above stay intact; only the bridge execution path is fail-closed.

## Verification strategy (RED → GREEN, no live)

MIX executable tests and static source-scan tests. PowerShell routes are STATIC
TEXT/ORDERING scans only — they do NOT execute PowerShell and do NOT mock a process
call. State this explicitly in each static test docstring (a "PowerShell runtime mock"
claim is a false-claim; the test only inspects source text/ordering).

- **Executable (valid RED→GREEN):** R2 `agent.main()` returns non-success before
  screenshot/XML/ADB/network/patch/git/resume (mocks `assert_not_called()`); R5
  `recovery_runtime.main()` with ALL enabling flags `--dispatch --enable-live-recovery
  --resume` returns non-zero and `ScheduleRecoveryRuntime.__init__` is never called;
  R6 `RecoverySupervisor.run(enable_live_recovery=True)` returns `AUTO_RECOVERY_DISABLED`
  before executors; R10 `Watcher.process_failure()` with a mock `RecoveryBridge` and
  `apply_recovery`/`recapture`/`retry`/`verify` ALL `assert_not_called()`.
- **Static (REGRESSION nodes, not runtime RED→GREEN):** R7 `test_watcher_disabled_no_start_process`
  asserts `$AUTO_RECOVERY_ENABLED=$false`, no override to `$true`, and the disabled
  guard `if` precedes `Start-Process` (and its `exit` precedes it). R8
  `test_register_action_disabled_no_live_recovery`. R11
  `test_healthwatch_disabled_no_resume_request`.
- **R9:** SOURCE_ONLY classification scan; record UNRELATED + no edit.

## Cross-repo test command (the key trap)

The Hermes venv has an **editable** `automation_core` via
`__editable__.automation_core-*.pth` that points at the COORDINATOR
`D:\Taadaa\automation-core` (NOT the `-implementation` worktree). So:

```bash
# BAD: env PYTHONPATH= resets the var to empty → editable .pth wins → resolves the
#      NON-implementation automation-core → AUTO_RECOVERY_ENABLED ImportError / wrong checkout
env PYTHONPATH= python -m pytest ...

# GOOD: keep a Windows-style (NOT /d/...) path to the impl core worktree
cd '/d/Taadaa/tiktok-luot nuoi acc-implementation'
env PYTHONPATH='D:/Taadaa/automation-core-implementation/src' python -m pytest -q \
  python_runner/tests/test_recovery_runtime_audit.py \
  -k 'recovery_runtime_disabled_fail_closed or recovery_runtime_parser_flags_resolvable'
```

`python_runner` is NOT installed — it resolves from the **cwd** (impl consumer), so run
pytest from the consumer impl worktree root. Consumer tests import `scheduler.*` via
`python_runner/tests/_path_setup.py`.

Probe to confirm provenance:
`python -c "from automation_core import global_recovery as g; print(g.__file__, getattr(g,'AUTO_RECOVERY_ENABLED', 'MISSING'))"`
— must print `...automation-core-implementation\src\...` and `False`.

## Test-authoring pitfalls (cost real cycles)

- **R10 mock bridge:** `Watcher.process_failure` with a `MagicMock` bridge returns
  `MANUAL_REQUIRED` (never reaching the guard) unless the bridge has
  `recovery_signature_allowlist` set to the snapshot's canonical signature
  (`{"failure-v1:FEED:E"}` for the P1 snapshot). Also `handler_id="h"` +
  `registered_handlers={"h": bridge}` so `_registered_handler_matches()` is true.
  Use the AUTO_RECOVERY_PENDING report shape from the existing P1 R2 tests.
- **R11 static test `find()`:** `text.find("Write-ResumeRequest")` matches the
  *function definition* (early in the file), not the *call site* inside
  `Invoke-HealthCheck`. Assert on the call occurrence instead, e.g.
  `text.find("Write-ResumeRequest -Path")` (and that the disabled `if (-not $AUTO_RECOVERY_ENABLED)`
  guard precedes it).
- **R5 RED check:** mock `ScheduleRecoveryRuntime.__init__` with a capture wrapper that
  still calls `original_init` — on current (unguarded) source the init runs and then
  `validate_required_handlers` raises `NO_HANDLER_IMPLEMENTED:required-registry-missing`
  → proves the runtime IS constructed/activated when disabled. After the guard, init is
  never reached and `construct_calls == []`.
- **parser regression test** `test_recovery_runtime_parser_flags_resolvable` parses
  `--dispatch/--enable-live-recovery/--resume` directly via `build_parser()` — it
  passes on baseline (parsing only resolves flags, doesn't toggle behavior) and is
  explicitly NOT a valid RED node.
