# Feed P1 RED/GREEN session — 2026-08-12 (tiktok-luot nuoi acc recovery adapter)

Continuation of `recovery-adapter-p1-discovery-2026-08-12.md` (discovery +
baseline phase). This file records the RED→GREEN attempt, the exact failures,
and the blocker that stopped the phase. The durable rules distilled from it
live in the SKILL.md section "Recovery-adapter migration — P1 RED/GREEN
implementation".

## Environment facts (verified this session)

- Worktree: `D:/Taadaa/tiktok-luot-nuoi-acc-recovery-adapter-p1-wt`, branch
  `recovery-adapter/feed-p1`, HEAD `ca324e8` (= base).
- Original repo `D:/Taadaa/tiktok-luot nuoi acc`: master @ `b34f410`, 7
  untracked paths unchanged (foreign commit `b34f410` arrived mid-discovery —
  worktree unaffected).
- Pin: `requirements-automation-core.txt` line 2 = 0.4.18 wheel
  (`file:///D:/CodexRuntime/automation-core-popup26-wheel-20260802/...`).
- Core repo `D:/Taadaa/automation-core` HEAD `3f63c87`, `pyproject.toml`
  version `0.4.45`, setuptools backend (`requires = ["setuptools>=68", "wheel"]`).
- Ambient hermes venv has automation_core **0.4.43** (no `escalation` module —
  `escalation.py` was added between 0.4.43 and 0.4.45).

## Wheel build (worked, one-shot)

```bash
V='C:/Users/Kibe/p1-feed-venv-20260812'; OUT='C:/Users/Kibe/p1-venv-wheels-20260812'
mkdir -p "$OUT"
"$V/Scripts/python.exe" -m pip wheel --no-deps -w "$OUT" 'D:/Taadaa/automation-core'
# -> automation_core-0.4.45-py3-none-any.whl, 215710 bytes
#    sha256 3d35fc543dc0c040a0b1ee912b09d4db499226b317ff56b73a46972bd01371c3
```

Notes: output dir must NOT be the core repo's `dist/` (in-repo untracked
pollution). A cached wheel from a prior build session has a different SHA —
both valid, record provenance. `pip wheel` needs no `build` module; PEP 517
isolated build works with the setuptools backend.

## Venv poison (the blocker)

`python -m venv C:/Users/Kibe/p1-feed-venv-20260812` from git-bash silently
created a venv whose `Scripts/python.exe` still resolves imports to the
HERMES venv site-packages (`...hermes-agent\venv\Lib\site-packages`). Proof:

```
$ "$V/Scripts/python.exe" -m pip install <wheel> pytest pillow
Not uninstalling automation-core at c:\users\kibe\appdata\local\hermes\hermes-agent\venv\lib\site-packages, outside environment C:\Users\Kibe\p1-feed-venv-20260812
Successfully installed automation-core-0.4.45
$ "$V/Scripts/python.exe" -c "import automation_core; print(automation_core.__file__)"
...\hermes-agent\venv\Lib\site-packages\automation_core\__init__.py   # WRONG
import automation_core.escalation -> ModuleNotFoundError               # WRONG
```

`python` in MSYS resolves to the hermes venv interpreter; `venv` then links
against it and inherits its site-packages on the path. Fix (applied in the
second pass, VERIFIED): create the venv with the REAL interpreter's absolute
path — `C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe -m
venv C:/Users/Kibe/p1-feed-venv-v2-20260812` (`py -3.11` has NO runtime on
this host) — then verify `sys.prefix`/`sys.executable` point at the new venv,
`sys.path` contains no hermes-agent entry, and run EVERY python/pytest command
with `env -u PYTHONPATH` (the global PYTHONPATH points at hermes site-packages
and re-poisons a clean venv — the true root cause of the earlier "broken"
venv). Recreate, don't repair.

## RED attempt #1 (hermes venv, 0.4.43) — wrong-env signal

`python -B -m pytest tests/test_recovery_adapter_pilot.py -q -p no:cacheprovider`
from `python_runner/`:

```
ImportError while importing test module ... test_recovery_adapter_pilot.py
tests\test_recovery_adapter_pilot.py:32: in <module>
    from automation_core.escalation import (
E   ModuleNotFoundError: No module named 'automation_core.escalation'
1 error in 1.31s
```

This is a REAL collection failure but for the WRONG reason (env too old, not
feature missing). Lesson: RED runs in the pinned 0.4.45 venv only; the hermes
venv baseline is only for pre-existing classification of the OLD suites.

## Allowlist deviation (self-caught, reverted)

Created `python_runner/flows/feed_recovery_adapter.py` (intermediate adapter
module) — NOT on the P1 patch allowlist (which permits only the 5 existing
files + CREATE of the test file). Deleted it immediately; `git status` back to
only `?? docs/ai/...md` + `?? python_runner/tests/test_recovery_adapter_pilot.py`.
Wiring must instead be added directly inside the allowlisted seam file
(`flows/feed_swipe_smoke.py` SEAM A at :1020-1043 terminal branch + the
manual-needed return point at :17311 `_feed_session_flow` tail, where `ctx` is
in scope) and `scheduler/recovery_handlers.py` (expose registry + escalation
registration helper). Test file imports those symbols from the allowlisted
modules.

## Core 0.4.45 API facts (read from source, not docs)

- `RecoveryQueue.finalize_failed_locked(target_id, reason=..., evidence=...)`:
  requires state in `_FAILED_LOCKED_SOURCE_STATES` (CLASSIFIED,
  RECOVERY_RESERVED, RECOVERING, RECAPTURED, GUIDED_RECOVERY_REQUIRED); never
  fabricates artifacts/attempts; durable event carries minimal redacted
  evidence. `_require_reservation` enforces token+owner in strict mode.
- `RecoveryQueue.__init__` strict=True rejects artifact_root under OneDrive or
  under any `.git` ancestor → tests must use tmp_path (pytest) / %TEMP%, never
  repo paths.
- `EscalationRegistry(budget=3 default)`: `register(hook)` validates
  `escalate` callable; `call()` redacts evidence+reason, consults ONLY
  `_hooks[0]` (no fall-through), wraps hook exceptions into
  `EscalationResult(FAILED, note="HOOK_RAISED:...")`. `proof_backed` requires
  SUCCEEDED + recapture + passed verifier with proof.
- `BatchRecoveryOrchestrator.run`: preflight isolates per-target
  NO_HANDLER_IMPLEMENTED (others in batch proceed); `_run_one` restart guard
  returns FAILED_LOCKED without detect when durable record is FAILED_LOCKED;
  cap exhaustion → `finalize_failed_locked` + `_failed_locked_hold` (lock kept,
  status `failed_locked`); verifier fail → `VERIFIER_FAILED` contract error →
  fail-closed FAILED_LOCKED; proof-backed hook success → intermediate
  `ESCALATION_REQUIRED` (never releases).
- `GlobalRecoveryPolicy`: meaningful 8 = live 7 + detection
  (`RECOVERY_CAP_MUST_EQUAL_DETECTION_PLUS_LIVE`), escalation_budget can only
  tighten.
- Old-pin guard idiom to mirror (`recovery_supervisor.py:26-33`):
  `try: from automation_core.global_recovery import GlobalRecoveryPolicy
   except ImportError: GlobalRecoveryPolicy = None` then fail closed.

## Execution outcome (second pass, same day) — 19 passed / 1 failed, NOT full green

The venv-fix + allowlist rewrite above were executed. RED/GREEN both ran in
the pinned venv v2 via `env -u PYTHONPATH <venv>/Scripts/python.exe -m pytest
-q python_runner/tests/test_recovery_adapter_pilot.py`:

- **RED** (production reverted to HEAD via `git checkout --`): collection
  error `ImportError: cannot import name 'CAPTURE_INVALID' from
  'flows.feed_swipe_smoke'` — 1 error, 0 collected. Correct "adapter chưa
  wire" reason (the seam import re-exports CAPTURE_INVALID/MANUAL_NEEDED_POPUP
  from `scheduler.recovery_handlers`, so a missing seam fails at import).
  Sequence used: `git diff <2 allowlist files> > /tmp/p1_seam.patch` →
  `git checkout -- <files>` → RED run → `git apply <Windows path>` → GREEN run.
- **GREEN**: 19 passed, 1 failed (2.69s). The 1 failure is the cap=1 durable-
  state trap documented in SKILL.md (result FAILED_LOCKED but durable queue
  state CLASSIFIED) — fix is `max_meaningful_attempts >= 2` in the test.
- **`git apply` could not open `/tmp/p1_seam.patch`** (native Windows git):
  MSYS `/tmp` maps to `C:\Users\Kibe\AppData\Local\Temp`; pass the Windows
  path. Also note the earlier wrong-file incident: a SEAM-A block intended for
  `flows/feed_swipe_smoke.py` overwrote `core/ui_capture.py` (restored with
  `git checkout --`; `ui_capture.py` stayed unmodified — SEAM B not needed).
- Final worktree status: `M requirements-automation-core.txt`,
  `M python_runner/flows/feed_swipe_smoke.py`,
  `M python_runner/scheduler/recovery_handlers.py`, plus the 2 pre-existing
  untracked (`docs/ai/recovery-adapter-discovery-feed-2026-08-12.md`,
  `tests/test_recovery_adapter_pilot.py`). No commit/push.

Remaining verification before the audit gate: fix the cap test (cap=2), rerun
to 20/20, run `test_recovery_supervisor.py` + `test_recovery_health_contract.py`
on venv v2 vs baseline (72+12; note pre-existing PIL `_imaging` collection
errors there), `py_compile` each edited file, `git diff --check`, EOL LF check
(`file`), `pm clear` scan, no-second-control-plane scan, original-repo
manifest unchanged, then handoff to the AG Opus P1 diff audit.

## Tool-output truncation workaround (recurring this session)

Several `terminal` calls returned exit 0 but the output was reduced to a
single line (multi-file grep/nl pipelines). Reliable workarounds used:
`read_file` with offset/limit on the exact line ranges, or a
`python - <<'PY'` heredoc that reads the file and prints numbered ranges.
Anchor on file+line, not on the truncated aggregate output.
