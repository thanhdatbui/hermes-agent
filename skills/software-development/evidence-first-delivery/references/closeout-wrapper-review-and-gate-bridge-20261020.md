# Closeout wrapper review and gate bridge (2026-10-20)

## Reusable lesson
A required visual artifact cannot be waived because a lower-level device guard rejects a raw capture command. The correct response is to make the evidence path compliant with the guard, then verify the artifact. Backend evidence (API state, client table, IP/proxy, runner status) does not replace a required screenshot.

## Canonical sequence
1. Inspect the target and bind machine ID, serial, and artifact scope.
2. Acquire `operator_device_lock` for the exact machine/serial.
3. Run the capture command through a canonical wrapper while the lease is held; preserve binary stdout/stderr and use a context manager so the lease is released on success and failure.
4. Save to a fresh, unique path; validate file existence, PNG structure/size, freshness, and target screen.
5. Run WinRT OCR or vision on the exact file. Reject Home/Launcher, black/dozing, stale, or mismatched captures.
6. Send `MEDIA:<absolute-path>` only after inspection and state in the response what was visibly confirmed.
7. Re-check the device lock aliases after capture and report release evidence separately.

## Guard-compatible wrapper contract
A wrapper such as `with_device_lock.py` should:
- default `force_preempt` to false; preemption must be explicit;
- accept an explicit serial or resolve it without swallowing unexpected exceptions;
- validate non-negative lock timeout;
- normalize `adb` to the configured executable without shell interpolation;
- run commands with `shell=False`, forward binary stdout/stderr, and propagate child exit codes;
- map missing executable/permission/lock-timeout failures to explicit exit codes;
- guarantee context-manager cleanup;
- emit minimal structured telemetry for acquire start, acquired, command finished, timeout, and release without secrets.

## Closeout/reviewer discipline
A focused test pass is necessary but not sufficient for `APPROVED`. Closeout review can reject a new wrapper for missing integration evidence, contention/cleanup coverage, telemetry, or guard compatibility. Validate Sol proposals with syntax checks before applying them: a proposal can be marked `valid` while containing an invalid replacement snippet. If Sol output is malformed, do not apply it; narrow the fallback contract and re-review the actual diff.

## Reporting pattern
Use concise status labels:
- `DONE`: all acceptance artifacts and reviewer approval are present.
- `UNPROVEN`: operational/backend checks pass but the required visual artifact or reviewer approval is missing.
- `BLOCKED`: a real external blocker remains, with its exact output/path.
Never say “all clear” while either the media gate or closeout gate remains open.
