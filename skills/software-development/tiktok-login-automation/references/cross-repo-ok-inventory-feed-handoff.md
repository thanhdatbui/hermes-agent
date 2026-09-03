# Cross-repo live handoff: popup OK → inventory/login → feed

## Trigger

Use when an operator asks to act on one live TikTok machine, then verify/reconcile accounts in `tiktok-log-in`, and finally return to `tiktok-luot nuoi acc`.

## Target and evidence gate

1. Resolve the named machine to exactly one valid ADB serial and the intended workbook row before any device action.
2. A safe workbook can contain a malformed value in `Device ID` (for example a date accidentally entered in that column). Do not edit the source workbook or silently choose among multiple serials. Exclude only values that fail the repository's ADB-serial shape, and proceed only when the remaining valid values collapse to exactly one serial. Record the malformed-row count without printing account or credential fields.
3. Check the central machine/serial lock. A backup/quarantine filename containing the machine number is not an active lock. Treat a live owner or unverifiable lock as blocked.
4. Capture fresh focus, screenshot, and ATX XML. For a requested `OK`, require one exact `OK` node that is enabled and clickable, retain its bounds, perform one semantic/ATX click, then capture fresh XML and screenshot. A click acknowledgement alone is not success; the marker must be absent afterward.

## Reconcile and login decision

Run the canonical reconciler only for the named machine, with one worker:

```text
cd /d/Taadaa/tiktok-log-in
env -u PYTHONPATH PYTHONNOUSITE=1 D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe -s scripts/reconcile_tiktok_accounts.py --workbook <target-scoped-safe-workbook> --machines <M> --adb-path <adb.exe> --source-runner D:/Taadaa/tiktok-luot nuoi acc --login-project D:/Taadaa/Tiktok_Reg --login-workbook <tracking-workbook> --proxy-mapping <proxy-map> --allow-live-reconcile --max-workers 1
```

- Keep the source workbook read-only; if a temporary filtered copy is needed to exclude one malformed mapping row, write it under the runtime artifact root and report that the source was unchanged.
- Read the generated per-target JSON summary, not only `DONE`. `login_attempts=[]` and `remaining_device_missing=[]` means inventory is complete and no login should run. Only missing device accounts with a usable TikTok ID/password may enter the login flow.
- Verify the reconciler's final lock handoff and ensure no active machine/serial lock remains before handing the device to the feed consumer.

## Return to feed

1. Use the actual `run-feed-session.ps1` parameter names. Its default behavior includes `--prepare-tiktok`; `-PrepareTikTok` is not a valid PowerShell switch and must not be invented.
2. If the device is on Launcher/Home, do not pass `-NoPrepareTikTok`: the feed runner then sees `com.sec.android.app.launcher` and stops `unknown TikTok state` before any swipe. Use the default preparation path to launch TikTok. If the target is already in a verified TikTok feed and preservation is explicitly desired, `-NoPrepareTikTok` can be used only after that fresh state is proven.
3. Run only the named machine and row. Inspect the machine-scoped summary, manifest, JSONL, exact XML, and matching screenshot. Accept feed success only when `final_status=success`, requested/completed swipes match, Profile verification is matched when enabled, and cleanup/lock state is recorded.
4. A successful feed child may launch an optional downstream hook (such as Follow). Keep the feed result separate from the hook result. If the hook produces no artifact or log progress and the exact wrapper remains alive, stop only that run's process tree after proving its command line is not an independent farm process. Do not claim the hook succeeded.

## Known failure signatures from this sequence

- `machine mapping ambiguous`: inspect valid serial shape and malformed workbook rows; never guess.
- `unknown TikTok state` with baseline `focused_package=com.sec.android.app.launcher`: preparation was skipped or the target was left on Launcher.
- `profile_preflight_switcher_*` ending in SystemUI/Recents: the feed may later recover and complete swipes, but the switcher branch itself is not proven. Keep branch coverage separate from overall feed success.
- `follow-hook` starts after feed cleanup and then stops producing artifacts: this is a downstream hook hang, not a feed failure.

## Reporting

Report in Vietnamese as `Mục đích → Kết quả → Bằng chứng → Blocker`, separating:

- popup action proof;
- inventory count and whether login was needed;
- feed terminal result and swipe/profile proof;
- downstream hook status;
- active-lock status.

Never print full serials, passwords, tokens, email addresses, or account workbook neighbors.
