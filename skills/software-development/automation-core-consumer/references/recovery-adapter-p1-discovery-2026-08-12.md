# Recovery-adapter P1 Discovery — `tiktok-luot nuoi acc` pilot (2026-08-12)

Reference for the discovery + baseline-only phase of the consumer
recovery-adapter migration (core pin 0.4.18 → 0.4.45, wire
`build_recovery_handler_registry()` into the feed-session runtime path,
register EscalationHook for MANUAL_NEEDED_POPUP). Reusable as a template for
the other 8 consumers in the migration plan.

## Scope discipline (what the brief mandated)

- Dedicated worktree from the EXACT pinned HEAD: `git worktree add -b
  recovery-adapter/feed-p1-discovery D:/Taadaa/<name>-p1-wt <full-sha>`.
  Original repo was dirty; NEVER reset/clean/stage/commit on it.
- Read-only discovery candidates (per plan, not pre-approved patch targets):
  `python_runner/run_tiktok.py`, `python_runner/scheduler/engine.py`,
  `python_runner/hermes_cron/watcher.py`, `python_runner/core/capture_recovery.py`.
  Other files may be READ to trace callers (ui_capture, feed_swipe_smoke,
  recovery_runtime, recovery_supervisor, recovery_handlers, launcher, tests).
- Forbidden reads: dirty/untracked paths, data/workbook/log/raw artifacts,
  .env/session/generated runtime, credentials.
- No live/ADB/device/TikTok/cron/subprocess side effects. No `pm clear`.
- Report only: `docs/ai/recovery-adapter-discovery-feed-2026-08-12.md`
  (Vietnamese), evidence outside the repo. No source/test/config/pin edits.
  No commit/push. Preserve EOL (LF).

## Preflight record (capture before any work)

- Repo identity: toplevel, HEAD sha, branch, worktree path/branch, core repo HEAD.
- Dirty snapshot of original repo: `git status --porcelain=v1
  --untracked-files=all` (paths/status only).
- Worktree must be clean at start; baseline uses `python -B` (no __pycache__).

## Baseline (exact command, run BEFORE writing the report)

```bash
python -B -m pytest -q -p no:cacheprovider \
  python_runner/tests/test_recovery_supervisor.py \
  python_runner/tests/test_chain_recovery_handlers.py \
  python_runner/tests/test_loading_recovery_handlers.py \
  python_runner/tests/test_recovery_health_contract.py \
  python_runner/tests/test_network_artifact_replay.py
```

Results observed (2026-08-12, hermes venv CPython 3.11, automation_core
0.4.43 installed — NOT the pinned 0.4.18):

- Combined command: 91 collected, 2 collection errors (PIL `_imaging`
  ImportError inside venv site-packages → environment-pre-existing, not repo),
  exit 2, 0 executed.
- Per-module (diagnostics only): `test_recovery_supervisor.py` 72 passed +
  8 subtests; `test_recovery_health_contract.py` 12 passed;
  `test_network_artifact_replay.py` FAILS collection standalone
  (`ModuleNotFoundError: core.classifier`) but collects fine in the combined
  command — pytest basedir/sys.path insertion differs; per-file loop would
  manufacture a fake pre-existing error.
- Interpreter/pin fact: `importlib.metadata.version('automation_core')` =
  0.4.43 in the ambient venv. Baseline green on a NEWER core than the pin is
  still valid evidence (closer to target 0.4.45) — label it, don't hide it.

## Call-chain trace (FACT path:line — feed-session runtime path)

```
run_tiktok.py:26          import feed_session_smoke
run_tiktok.py:959-960     feed-session-smoke → feed_session_smoke(ctx)
run_tiktok.py:967-968     multi-machine-feed-session → execute_multi_machine_feed_session(ctx)
run_tiktok.py:971         lock_succeeded = _is_verified_success(result)
→ flows/feed_swipe_smoke.py:17701 feed_session_smoke
  → :14360 _feed_session_flow (main swipe loop)
    → :990 _capture_xml_text(ctx, step)   [called at 3425/3617/3713/11094/11205/11857/12379/12499/12885/13953]
      → core/ui_capture.py:1008 capture_required_ui
        → :94 capture_required_ui_result
          → :146-163 capture_once() = capture_ui_xml(...)
          → UIDumpError ladder: :170 recover_adb_transport
            :186 recover_uiautomator_foreground_service
            :199 recover_uiautomator_direct_capture_after_shell_exit
            :217 recover_capture_stack  (core/capture_recovery.py:7263)
            :228 recovery_preflight_reason
            :241-253 raise UIDumpError("CAPTURE_RECOVERY_ATTEMPT_BUDGET_EXHAUSTED",
                                      attempts=[{recovery_state: "FINAL_BLOCKED"}])
            :257 recover_capture_deadline (core/capture_recovery.py:7724,
                                           callbacks=recovery_callbacks, failure_signature=exc.code)
        ← UIDumpError propagates
      ← feed_swipe_smoke.py:1020-1043  SEAM: terminal_recovery branch
           (code == CAPTURE_RECOVERY_ATTEMPT_BUDGET_EXHAUSTED
            or any attempt recovery_state == "FINAL_BLOCKED")
           → log result="capture-invalid" + raise (terminal journal supersedes heuristics)
      ← :1045-1061 non-terminal → log "skipped" + return None
```

Scheduler/supervisor side (separate process — NOT in-process feed):

```
scheduler/__main__.py:20-33  Scheduler(run_shift=run_launcher_shift); --live required
scheduler/launcher.py:18-40  build_launcher_command → powershell run-feed-session.ps1
scheduler/launcher.py:125    run_launcher_shift (subprocess)
scheduler/engine.py:58-77    Scheduler; :202-232 _execute_and_log → :205 run_shift
scheduler/recovery_runtime.py:2928   build_recovery_handler_registry()  ← ONLY call site
  :2930-2950  inject into RecoveryRuntime / ScheduleRecoveryRuntime
  :1032-1039  validate_required_handlers (fail-closed)
  :1700/:2101 validate_handler_gate (pre-live)
  :2651-2755  ScheduleRecoveryRuntime.run_once: terminal_shifts() → :2685
              discover_incidents_from_scheduler_log → :2748 run_incidents
scheduler/recovery_supervisor.py:741-807  validate_handler_gate contract
  :760 isinstance(CoreRecoveryHandlerRegistry), :767 validate_required,
  :768 require, :777 callbacks, :779-781 failure_classes, :796-798 digest,
  :799-804 verifier/tests/lease, :805-806 attempt cap
scheduler/recovery_supervisor.py:1142-1162  _SENSITIVE_MARKERS incl. MANUAL_NEEDED_POPUP (:1151)
scheduler/recovery_handlers.py:689-713  registry: CAPTURE_INVALID + MANUAL_NEEDED_POPUP
  :28 REQUIRED_FAILURE_CLASSES = (CAPTURE_INVALID, MANUAL_NEEDED_POPUP)
hermes_cron/watcher.py:205-212  Watcher with registered_handlers bridge (separate journal pipeline,
  NOT build_recovery_handler_registry); :259-391 process_failure DETECTED→...→VERIFIED_SUCCESS|FINAL_BLOCKED
```

## Gate answer (the question the plan requires)

`build_recovery_handler_registry()` is scheduler/supervisor-gate-only:
constructed at `recovery_runtime.py:2928`, consumed via
`validate_required_handlers`/`validate_handler_gate`. The in-process feed
session path (run_tiktok → feed_swipe_smoke → ui_capture → capture_recovery)
never imports registry/runtime/supervisor/classify_incident; it has its own
flow handlers (`flows/recovery_handlers.py:211` uses `classify_tiktok_screen`)
and capture ladder (`CaptureRecoveryCallbacks`).

## Seams (offline-testable)

- **SEAM A (recommended):** `flows/feed_swipe_smoke.py:1020-1043` — terminal
  recovery branch; pure UIDumpError handling, module already covered by
  hundreds of offline tests (patch `_capture_xml_text` /
  `core.ui_capture.capture_ui_xml` with side_effect lists).
- **SEAM B:** `core/ui_capture.py:110-112` — `capture_recovery_callbacks`
  kwarg (type `CaptureRecoveryCallbacks`, `capture_recovery.py:244`) already
  type-checked and forwarded to `recover_capture_deadline(callbacks=...)`;
  feed flow currently does NOT pass it.
- **SEAM C (existing, green):** scheduler-side adapter
  (`recovery_runtime.py:2928` → run_once → run_incidents → classify/gate).

## Pin / import contract check (read-only)

- Pin: `requirements-automation-core.txt:2` →
  `automation-core @ file:///D:/CodexRuntime/automation-core-popup26-wheel-20260802/automation_core-0.4.18-py3-none-any.whl`
- Target: core repo `pyproject.toml:7` `version = "0.4.45"`
- Core 0.4.45 source names: `__init__.py:56,83-84` exports RecoveryHandlerRegistry
  /RecoveryHandlerSpec/RecoveryQueue/RecoveryTarget/require_recovery_handler/
  RecoveryCompletionGate/RecoveryContractError; `recovery.py:67,85,101,108`
  register/require/validate_required; `escalation.py:31,78,96,105,122`
  DEFAULT_ESCALATION_BUDGET=3, EscalationHook Protocol, EscalationRegistry.

## Conclusion + report anatomy

- Verdict `READY_FOR_P1_IMPLEMENTATION` (seam A proven offline-testable;
  registry+gate already green on core 0.4.43; `_SENSITIVE_MARKERS` has
  MANUAL_NEEDED_POPUP; `pm clear` = 0 in non-test python_runner). No
  live-connected claims.
- Report sections: preflight (identity/base/dirty snapshot), baseline (exact
  command + counts + pre-existing classification + interpreter/pin note),
  discovery trace (FACT path:line per file), gate answer, seams, pin contract,
  conclusion, files read / files NOT read (forbidden), post-write verification.
- Post-write: independent re-read + hash/stat, markdown/diff check, tracked-file
  digest manifest (git ls-files → sha256+size JSON before/after) to prove no
  source/test/config changes, original-repo status manifest compare + reflog
  attribution (see concurrent-workspace-safety pitfalls: a foreign writer
  committed the dirty `scripts/run-proxy-watcher.ps1` as `b34f410` mid-session).

## Assumptions / NEEDS_PROOF left for P1 implementation

- multi-machine-feed-session shares seam A (traced to child `feed_session_smoke`
  at multi_machine_feed_session.py:952; not deeply traced).
- Binary compat of wheel 0.4.45 with consumer's CoreRecoveryHandlerRegistry use
  (baseline ran against 0.4.43; source names match).
- hermes_cron/watcher.py hook scope (separate pipeline; out of P1 discovery scope).
