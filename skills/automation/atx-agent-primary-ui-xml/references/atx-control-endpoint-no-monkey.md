# ATX control endpoint: no-monkey verification

## Why this exists

On the Taadaa farm, `monkey -p com.github.uiautomator 1` is not an acceptable recovery or test action. It launches the UiAutomator package as an Android activity and can steal foreground from TikTok or leave the device on Launcher, destroying the failure scene. A successful process/ADB return code is not evidence that the original app remained foreground.

## Allowed one-device experiment

Use only after proving the target is idle from authoritative lock metadata and ADB state, and never use machine 59 or a currently scheduled/locked target.

1. Capture pre-action focus/package/activity and ATX health/XML through `capture_atx_session_ui`; do not use shell `uiautomator dump`.
2. Call only the ATX-agent internal control endpoint through the target serial:
   `adb -s <serial> shell /data/local/tmp/atx-agent curl -X POST http://127.0.0.1:7912/uiautomator`
3. Capture fresh focus/package/activity and ATX session XML immediately after the call.
4. Accept only if the endpoint response is bounded, ATX returns `VERIFIED_HEALTHY` with parseable XML, and the foreground package/activity is unchanged (or any change is explicitly explained by the endpoint evidence).
5. If focus changes, the device is not idle, lock status is uncertain, ATX capture fails, or the endpoint response is ambiguous: stop after that single target and report `FINAL_BLOCKED`; do not try another machine.

## Production recovery boundary

The endpoint is a control-plane request to atx-agent, not permission to launch an Android UI activity. It may be used only in a target-scoped recovery handler after `ATX_SESSION_STUB_NOT_RUNNING` is classified. Re-discover the exact PID and target-scoped forward, then use pid-scoped `dumpWindowHierarchy([true])`. Verify focus after the control call and after the capture. If the expected app is no longer foreground, preserve the scene and fail closed; do not relaunch TikTok, press HOME/BACK, or invoke monkey.

## Evidence to report

- target machine/serial and lock preflight evidence;
- pre/post focused package and activity;
- endpoint exit/status and bounded response summary;
- ATX health, XML byte length, verifier result, PID and forward ownership;
- whether any code, device state, account, workbook, cron, or lock was changed.

## Live verification 2026-08-24 (machine 31, ce0416041bdb271305) — PASSED

Result: `POST /uiautomator` started the stub (`com.github.uiautomator` pid 21282 appeared in `ps -A`) and did NOT
change foreground — `mCurrentFocus`/`mResumedActivity` stayed `com.sec.android.app.launcher/.activities.LauncherActivity`
with identical window token across pre/post checks (~2 min apart). Endpoint exit=0,
atx-agent log: `Successfully started <nil>` (this `<nil>` is normal even on success).

Race pitfall after stub cold-start: an immediate pid-agnostic `POST /jsonrpc/0 dumpWindowHierarchy` returned
**HTTP 200 with EMPTY body (SIZE=0)** while the stub was still binding its socket; first attempt ~18s after the
endpoint call was still empty. Retry loop succeeded on the next pass (~90s after start): HTTP 200,
13KB XML with `<hierarchy>`. So treat `200 + empty body ≠ healthy` — poll until the XML contains `<hierarchy`
instead of trusting the status code alone.

Useful pre-state signature confirmed: agent running (`ps -A` shows `atx-agent`) + stub absent → persistent
`/jsonrpc/0` answers **HTTP 502** with empty body BEFORE the control call; this is exactly
`ATX_SESSION_STUB_NOT_RUNNING`, i.e. the correct precondition for this handler.

Evidence artifacts: `C:/Users/Kibe/AppData/Local/hermes/cache/atx-uiautomator-probe-20260824-m31/`
(pre/post focus dumps, endpoint_response.txt, post_jsonrpc.json). Cleanup rule honored: only the forward this
session created was removed (`forward --remove tcp:<own-port>`); pre-existing foreign forwards on the same
serial were left untouched.
