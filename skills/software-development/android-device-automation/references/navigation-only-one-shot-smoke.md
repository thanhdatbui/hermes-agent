# Audited one-shot Android navigation smoke

Use this pattern for a live smoke that may launch an app and perform bounded navigation input, but must never execute the business action being protected (for example, tapping **Follow**).

## Failure mode that motivated the pattern

A shell command can report apparent success while producing no usable UI evidence:

- `uiautomator dump ...` exits `0`;
- stderr contains `could not get idle state`;
- the remote XML file does not exist;
- `dumpsys activity` still proves the target app is the exact foreground package.

Therefore, **exit code and foreground are not UI-capture proof**. Verify the returned XML itself through the canonical public capture API.

## Canonical capture contract

Prefer the installed public API and inspect its live signature before building the harness:

```python
from automation_core.adb import AdbClient
from automation_core.persistent_ui import capture_persistent_ui
from automation_core.ui_capture import PersistentHealth

result = capture_persistent_ui(
    AdbClient(adb_path=adb_path, serial=serial, default_timeout=timeout),
    timeout=timeout,
    restart_attempts=0 if restart_budget_consumed else 1,
)
```

Every capture must be fail-closed in this order:

1. Prove the exact device lease is still owned by this process/run.
2. Prove the host mutex is held.
3. Prove watcher identity and scheduled-task XML are unchanged.
4. Prove Android VPN readiness.
5. Prove the resolved app component belongs to the exact package.
6. Prove the exact package is foreground before capture.
7. Call `capture_persistent_ui`.
8. Require all of:
   - `result.health == PersistentHealth.VERIFIED_HEALTHY`;
   - non-empty `result.xml`;
   - `result.verification.valid is True`;
   - XML package/resource-id evidence belongs to the exact target package and not launcher/SystemUI;
   - at least one capture attempt reached ADB forward setup;
   - every reached forward has `forward_exit_code == 0` and `forward_remove_exit_code == 0`;
   - the exact package is still foreground after capture.
9. On any failure, set the adapter's sticky denied latch before returning control to production navigation code.

Do not call private `_recover_uiautomator`, hand-roll `/sdcard/window_dump.xml`, or treat a shell dump's `returncode == 0` as verified capture in an audited consumer harness.

## One restart budget for the whole run

The persistent service restart allowance is **run-global**, not per capture:

```python
restart_attempts = 0 if restart_budget_consumed else 1
result = capture_persistent_ui(..., restart_attempts=restart_attempts)
if any(a.get("service_restart") is True for a in result.attempts):
    restart_budget_consumed = True
```

If the helper raises while a restart was allowed, conservatively latch the budget as consumed and fail the run. The caller cannot prove whether the helper crossed the restart boundary before raising. Never compensate with an app relaunch, reboot, force-stop, or hidden retry.

Record only redacted capture metadata: stage, health, verification boolean, node count, attempt count, restart allowed/used/consumed, and forward-cleanup proof. Never put raw XML, serial, account text, or exception payloads into the manifest.

## Bind launch proof to the correct ledger entry

A capture pre-gate can append another entry after the launch gate. This makes the following unsafe:

```python
launch()
wait_and_capture()
inputs[-1]["foreground_exact_after"] = True  # may modify capture entry
```

Keep the launch gate object itself, then update that object after capture and a fresh foreground check:

```python
launch_gate = inputs[-1]
assert launch_gate["stage"] == "LAUNCH_EXACT_COMPONENT"
if not wait_and_capture() or not foreground_exact():
    deny()
launch_gate["foreground_exact_after"] = True
```

Add a regression test with two ledger entries to prove the launch entry—not the later capture entry—receives the post-launch proof.

## Audit, preflight, authorization, run

The safe order is:

1. Freeze the fresh scope and exact production hashes.
2. Run targeted tests, full production tests, compile/import, AST/static-callgraph, and tracked-tree checks.
3. Build a byte-complete audit prompt.
4. Require the audit response to be exactly `b"APPROVED"` (8 bytes, no newline, BOM, spaces, or reasoning text).
5. Run the **final live preflight before minting authorization**:
   - HEAD equals the audited HEAD and expected remote;
   - audited harness/test/prompt/response hashes are unchanged;
   - only explicitly protected untracked files exist;
   - no matching harness process is running;
   - machine-to-serial binding is exact and uniquely online;
   - VPN, watcher identity, task XML, and host mutex are healthy;
   - inspect both machine and serial lock aliases and group them by lock/run ID;
   - verify owner PID liveness, host, project, status, and protocol.
6. If any live foreign owner holds either alias, stop. Do not mint authorization, kill it, release it, or use FULL_SCOPE takeover.
7. Only after all checks pass, mint a short-lived parent-owned one-shot authorization bound to the exact runner, test, prompt, response, run ID, machine, and HEAD hashes.
8. Immediately run the harness once. If authorization is consumed and acquisition/input later fails, do not retry that scope; build a fresh scope and repeat audit/authorization.

Audit approval does not reserve the device. A live lock discovered after audit is a normal `BLOCKED_SAFE` outcome, not permission to broaden takeover.

## Lock terminal states

Success:

- prove the destination and final Feed;
- prove the watcher final gate;
- call ownership-aware `release_with_audit`;
- verify the released alias count and exact run ownership before reporting success.

Failure after lease acquisition:

```python
lease.finish(succeeded=False, failure_status="failed_locked")
proof = verify_device_lock_lease(lease, "failed_locked", run_id)
```

Require proof for every alias: exact run ID, status `failed_locked`, inactive owner, and expected path count. Do not release or auto-retry. Opening a retained lock is a separate explicit operator action.

## Business-action denial and terminal evidence

For a navigation-only smoke:

- the adapter must expose no callable path that can issue the protected action;
- deny protected text/resource IDs and any coordinate overlapping such nodes;
- every tap/type/back uses a fresh semantic rebind and an input gate;
- no first-match, index, broad card-center, or absolute-coordinate fallback;
- manifest and final output keep `follow_action_invoked=false` (or the equivalent protected-action field);
- `VERIFIED_SUCCESS` requires the exact destination, final Feed, watcher final proof, and audited lease release;
- every other outcome is `FINAL_BLOCKED` with verified lock retention when a lease was acquired.

Choose evidence policy before audit. If raw source pixels/XML are forbidden, persist only sanitized XML, hashes, and synthetic/redacted evidence. If the operator requires an independent real screenshot for diagnosis, use a separate explicitly authorized read-only diagnostic scope and clean raw artifacts after review; do not silently widen the production smoke's evidence scope.

## Minimum regression matrix

- canonical healthy capture accepted;
- unavailable/unhealthy, missing XML, malformed XML, wrong package, launcher/SystemUI evidence rejected;
- failed/missing forward cleanup rejected;
- foreground lost after capture rejected;
- pre-gate failure proves the capture helper was never called;
- helper exception consumes the restart budget and leaves no raw data in events;
- only one restart is possible across multiple captures;
- sticky denial prevents later input;
- launch proof remains bound to the launch gate;
- source AST contains no manual `uiautomator`, remote dump path, or private recovery import;
- exact 8-byte audit verdict accepted; newline/space/BOM variants rejected without consuming authorization;
- live foreign machine/serial lock prevents authorization minting;
- failed lease becomes independently verified `failed_locked`.
