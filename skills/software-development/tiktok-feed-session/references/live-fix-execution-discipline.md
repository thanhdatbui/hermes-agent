# Live Fix Execution Discipline

## Purpose

Use this checklist whenever a consumer-side TikTok fix is paired with named live machines. Offline tests prove code behavior; they do not prove that the live classifier reached the branch, the device was safe to touch, or locks were handed off.

## Ordered workflow

1. Record the baseline:
   - `git status --short` and the pre-existing diff scope.
   - Target serials, machine/account mapping, lock files, owner PID/status.
   - Upload/consumer processes separately from the shared lock store.
   - `export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH"; which adb; adb devices`.
2. Add a routing regression before production code:
   - fixture must contain the real localized markers;
   - make the forbidden shared/core path raise if called;
   - assert the exact ADB command and selector geometry;
   - assert post-action focus/package and known-screen verification;
   - assert failure when recapture is unknown, sensitive, or not TikTok-focused.
3. Patch the smallest consumer file only. Read the full file or use a context-rich unified patch. Check CRLF/LF bytes before and after every edit. Re-read the edited region and run `py_compile` immediately.
4. Run focused tests, then the requested suites, `py_compile`, and `git diff --check`.
5. Run live targets before writing the final report. Reserve enough execution budget for the live command and artifact inspection; do not spend the final calls on optional exploration.
6. For each target, inspect `summary.txt`, `run_manifest.json`, `log.jsonl`, final screenshot/UI XML, focused activity, and `recovery_lock_handoff.json`. A batch exit code is not a per-machine result.
7. Verify both machine and serial locks are released or explicitly classify the target as blocked/held with the reason. Never delete an active `running`/`recovery` lock.

## Popup evidence contract

For a localized Add-phone popup, preserve all of:

- before screenshot;
- raw UI-dump command output;
- raw UI XML (even if the dump failed);
- focused activity/package;
- selector source (`consumer-add-phone` versus `image-add-phone`);
- tap coordinates and bounds;
- after screenshot/UI XML/focus;
- final result and lock handoff.

A screenshot can prove that `Thêm số điện thoại` is visible while a failed `uiautomator dump` proves the typed XML detector was not reached. In that case report `popup-visible / typed-branch-unverified`, not `direct-match-live-verified`. Do not silently substitute screenshot evidence for an XML match.

## Status vocabulary

- `RECOVERY_FIXED`: every named target has terminal live evidence, expected post-state, and lock handoff.
- `LIVE_PARTIAL`: code/tests are complete but one or more named live actions or final artifacts are still missing.
- `LIVE_BLOCKED`: a safety gate or concrete infrastructure failure prevented the authorized action; preserve evidence and name the exact stage.

Never collapse `LIVE_PARTIAL` or `LIVE_BLOCKED` into a successful batch status.

## Patch-tool pitfall

A short anchor such as a repeated test method name can match many places in a large CRLF file. If a patch result removes nearby lines or reports a partial-read warning, stop, reread the affected region, restore the file, then apply a unified patch with unique surrounding context. Normalize EOL only deliberately and verify `git diff --check` afterward.
