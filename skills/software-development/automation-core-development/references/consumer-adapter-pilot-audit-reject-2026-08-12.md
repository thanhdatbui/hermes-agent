# Consumer adapter pilot audit REJECT — 3 MAJOR + 3 MINOR (2026-08-12)

Commit `2c2e21d` ("feat(feed): nối RecoveryHandlerRegistry + EscalationHook
vào runtime path, pin core 0.4.45") in worktree
`D:\Taadaa\tiktok-luot-nuoi-acc-recovery-adapter-p1-wt` (branch
`recovery-adapter/feed-p1`). AG Opus verdict: **REJECT** — despite
20/20 focused tests green. Findings below are the pattern catalog for
consumer-boundary fail-closed audits; all fixes verified 20/20 again.

## MAJOR

### M1 — twin registration wrappers must share validation
- `flows/feed_swipe_smoke.py` `register_feed_recovery_escalation` validated
  `hook is None or not callable(getattr(hook, "escalate", None))` → TypeError.
- `scheduler/recovery_handlers.py` `register_escalation_hook` (the twin)
  had ZERO validation: silently registered `None`/non-conforming objects.
  Core `EscalationRegistry.register` does validate, but the audit reads the
  CONSUMER boundary — one wrapper validating and its twin not is a finding.
- Fix: identical TypeError gate in both wrappers + `pytest.raises(TypeError)`
  tests for `None` and `object()`.

### M2 — never mix consumer enum values into a result dict core switches on
- `classify_manual_needed_popup` no-hook branch returned
  `"status": ExitStatus.MANUAL_NEEDED.value` (`"manual-needed"`, consumer
  enum) while hook/proof branches used `FinalResultStatus.*.value` (core
  enum). Downstream dispatch on `FinalResultStatus` never matches
  `"manual-needed"` → terminal silently dropped to unhandled state
  (fail-closed bypass).
- Fix: `"status": FinalResultStatus.FAILED_LOCKED.value` uniformly; keep
  consumer nuance as `"manual_needed": True`.
- Test had hard-coded `result["status"] == "manual-needed"` — a string-match
  that MASKED the type inconsistency. Update the test with the fix.

### M3 — one registry owner
- `_feed_recovery_queue()` built the queue AND assigned `queue.registry =
  build_recovery_handler_registry()`; `FeedRecoveryAdapter.__init__` then
  overwrote `self.queue.registry = self.registry` (registry kwarg or second
  `build_recovery_handler_registry()` call) → double construction + silent
  swap if caller passed a different registry.
- Fix: helper returns plain queue state (deleted the registry assignment);
  adapter is the single owner: `self.registry = registry or
  build_recovery_handler_registry(); self.queue.registry = self.registry`.

## MINOR

### m1 — dead exported API in a security-sensitive module
- `expose_recovery_registry()` (no callers, no tests) added surface to
  `recovery_handlers.py`. Removed body AND `__all__` entry. Audit phrase
  "unnecessary API surface" ⇒ delete, don't leave it.

### m2 — vacuous redaction assertions (fake-green)
- Test asserted `"123456"`, `"do-not-store"`, `"jwt-like-secret"` were absent
  from evidence — but those strings were NEVER injected into evidence, so the
  assertion always passed and proved nothing about redaction.
- Fix: adapter now places real fixture secrets (`ctx.device_id`,
  `ctx.account`) into evidence; test asserts raw values gone AND
  `"<redacted>"` (core `redact_value` marker) present in the joined values.

### m3 — brittle core-behavior assumption without provenance
- `test_register_hook_idempotent_and_typed` asserted
  `escalation.hook_count == 1` after registering the same hook twice.
  Correct (core dedups by identity: `escalation.py:125-126` `if hook not in
  self._hooks`), but undocumented → future core change silently breaks or
  the test appears random. Fix: comment citing the exact core lines.

## Environment notes (reproduced for the auditor)

- Self-built wheel `C:/Users/Kibe/p1-venv-wheels-20260812/
  automation_core-0.4.45-py3-none-any.whl`,
  sha256 `3d35fc543dc0c040a0b1ee912b09d4db499226b317ff56b73a46972bd01371c3`,
  built from core HEAD `3f63c87` (contains `escalation.py`, `adapters.py`).
- Fresh venv `C:/Users/Kibe/p1-feed-venv-v2-20260812` from the REAL Python
  3.12 (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe` —
  `py -3.11` launcher does NOT exist on this host; uv's 3.11 is at
  `C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11.15-...\python.exe`).
- First venv attempt failed because the PERSISTED global `PYTHONPATH` points
  at the hermes venv site-packages → `import automation_core` resolved to the
  hermes copy. Fix: `env -u PYTHONPATH` prefix on every command, then verify
  `automation_core.__file__` is INSIDE the target venv + `pip show
  automation-core` == 0.4.45.
- Baseline: `test_recovery_supervisor.py` 72 passed + 8 subtests,
  `test_recovery_health_contract.py` 12 passed; pre-existing PIL `_imaging`
  collection errors in `test_chain_recovery_handlers.py` +
  `test_loading_recovery_handlers.py` (never claimed as new).
- Pilot suite after fixes: 20 passed in ~2s; focused supervisor+health 84
  passed + 8 subtests. RED evidence: revert seam → collection error
  `ImportError: cannot import name 'CAPTURE_INVALID' from
  'flows.feed_swipe_smoke'`.