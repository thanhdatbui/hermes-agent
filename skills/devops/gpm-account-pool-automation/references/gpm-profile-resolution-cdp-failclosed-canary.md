# GPM profile resolution → CDP fail-closed canary

## Trigger
Use when a pure Google login flow reports success after GPM Local API/CDP trouble, or when a reviewer flags ambiguous GPM/local-browser fallback.

## Reproduction pattern
1. Resolve the account email through GPM Local API. A valid unique match returns a concrete `gpm_profile_id`.
2. Start the profile through `/api/v3/profiles/start/{id}?skip_proxy_check=true` and read `remote_debugging_address`.
3. Connect with Playwright `connect_over_cdp`.
4. Force start/CDP failure in a mocked test, then run the real focused test suite.

## Required invariant
Once a non-empty GPM profile ID has been resolved, a later start/CDP failure must fail closed. Do not launch a separate local persistent context, because that browser may authenticate a different storage/profile while emitting a misleading `login_only_success`.

Expected behavior:
- return `GPM_START_FAILED` (or the flow's equivalent failure status);
- emit structured `gpm_start_failed` telemetry;
- do not call `launch_persistent_context` fallback;
- set `gpm_started = True` only after the start API succeeds;
- do not call stop for a profile whose start never succeeded.

Local persistent-context fallback is permitted only when no GPM profile ID was resolved and an explicitly valid local profile directory exists.

## Evidence pattern
A live canary exposed the bug when M55 resolved `55 - namdung150755@gmail.com - 5121`, CDP returned `ECONNREFUSED`, and the old code fell back to local launch before reporting `login_only_success`. The corrected offline focused suite covered this branch and finished `47 passed`; the closeout reviewer still required a fresh canary receipt and strict score >=85, so test success alone must not be reported as production approval.

## Closeout checklist
- `py_compile` passes.
- Focused tests assert status, telemetry, fallback non-invocation, and cleanup ownership.
- Live canary receipt is fresh and bound to the current scope/diff.
- `done_gate.py` and `closeout_gate.py` both pass the applicable strict thresholds.
- Do not call a Grace/Tier result `APPROVED` when the session requires >=85.
