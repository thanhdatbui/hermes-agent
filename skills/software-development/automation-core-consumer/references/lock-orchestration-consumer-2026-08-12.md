# Shared-core lock orchestration for consumer session engines (2026-08-12)

Session-derived from tiktok-follow P5 (phase lock/orchestration for
`FollowEngine.run_session`). Consumer-side only — `automation_core` untouched.

## Contract (as implemented in tiktok-follow, follow_engine.py)

Order: busy pre-check (lock-store read + video-process `wmic` scan, the
PROJECT_RULES PITFALL that shared-core cannot see) → device lease → workbook
lease → startup contract. Locked anywhere before startup ⇒ `SKIPPED_LOCKED`
with ZERO device ops and ZERO follow-state writes.

```python
@dataclass
class _LockLeases:
    device: object | None = None   # DeviceLockLease | fake
    workbook: object | None = None  # WorkbookLockLease | fake
    run_id: str = ""

class SharedCoreLockFactory:  # production default, lazy imports
    def acquire_device(self, *, machine, serial, run_id):
        from automation_core.device_lock import acquire_device_lock
        return acquire_device_lock(machine=machine, serial=serial,
            project="tiktok-follow", run_id=run_id, status="running",
            command=f"tiktok-follow follow run machine={machine}")
    def acquire_workbook(self, *, path, run_id):
        from automation_core.workbook import acquire_workbook_lock
        return acquire_workbook_lock(path, metadata={"project": "tiktok-follow",
                                                     "run_id": run_id})
```

Acquire: device first; on ANY workbook exception → rollback the owned device
lease (`release_with_audit`), and if the rollback itself errors the skip becomes
MANUAL_REVIEW (never a clean skip with an unreleased lease).

Release (finally): workbook first, then device. Proof = `released_paths` from
`release_with_audit(reason=...)`. Failure = exception OR empty `released_paths`
while `lease._released` is still False. All release errors → `details` +
MANUAL_REVIEW if the result isn't already failed. Core detail: `_released` is
set only `if released:` (strict=False release returns `[], {}` silently on
FileNotFound/ownership-mismatch), which is exactly why the empty-proof check
needs the `_released` probe.

## Classification table (fail closed)

| Shared-core exception | Result |
|---|---|
| `DeviceLockUnavailable` (active/foreign/busy) | `SKIPPED_LOCKED` |
| `DeviceLockReadinessError` (proxy/VPN not ready) | `SKIPPED_LOCKED` |
| `workbook.WorkbookError` (`BLOCKED_*`) | `SKIPPED_LOCKED` |
| `DeviceLockTransactionError` (guard/write/rollback) | `CONFIG_ERROR` |
| any other exception | `CONFIG_ERROR` (never proceed) |

Lazy-import the exception classes inside a classifier helper so the consumer
module imports without automation-core (offline test envs, import-order checks).

## Mode gating for not-yet-built modules

`importlib.util.find_spec("follow_runner.flows.mode2_follow_followers")` —
missing → CONFIG_ERROR when the session produced nothing else, else
`details["mode2"] = "NOT_IMPLEMENTED"` and keep prior results. Never eager-import
a module that doesn't exist (the old `from .mode2_... import run_mode2` inside
`run_session` would ImportError-crash the default "both" mode).

## Test traps (all reproduced live)

1. **Empty list is falsy** — `device_released_paths or ["defaults"]` replaces
   `[]` with the default, so the release-unverified branch is never exercised.
   Fix: `X if device_released_paths is None else device_released_paths`.
2. **Fake lease `_released` semantics** — the fake must set `_released=True`
   in `release_with_audit` ONLY when released paths are non-empty, mirroring
   core. An unconditional set makes the engine's "release unverified" check
   (`not released_paths and not _released`) dead code in tests.
3. **Helper kwargs routed into config** — a test helper like
   `_engine(factory, tmp_path, **over)` that feeds `config_from_dict` silently
   swallows `switcher_fn`/`identity_fn`/`busy_check` (unknown keys → `extra`),
   so the engine runs the real default path (e.g. real `_identity_matches`
   needing UI queues) and fails confusingly. Engine injectables must be explicit
   keyword params of the helper, separate from config overrides.

## Verification (this session)

59 pytest cases green with `PYTHONPATH="D:/Taadaa/automation-core/src;."`:
21 in `test_follow_engine.py` + `test_lock_orchestration.py` (new file with
FakeLockFactory + FakeLease), 38 in the untouched suites. `git diff --check`
clean; `follow_engine.py` kept pure CRLF (492/492/492) via the byte-exact
replace-script recipe; module imports without automation-core on the path.
Worker-owned concurrent files (mode1/verify/adapter + their tests) untouched —
baseline `git status` captured before editing, re-checked after.
