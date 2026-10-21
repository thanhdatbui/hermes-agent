---
name: live-profile-mutation-recovery
description: "Use for live TikTok profile mutation recovery."
---

# Live TikTok Profile Mutation Recovery

Use this class-level workflow for pinning videos, changing avatars, editing profile metadata, or any other live mutation on a farm Android device when target identity, UI state, and post-action result must be proven.

## Non-negotiable completion contract

A dry-run, worker exit code, queue state, workbook flag, or local asset marker is not completion proof. Completion requires:

1. Exact machine/serial mapping from the canonical O(1) inspection tool.
2. Fresh UI evidence showing the intended account and intended profile surface before mutation.
3. The live action performed through the bounded runner with the correct device lock.
4. Independent post-action read-back from the exact account.
5. A fresh screenshot inspected with vision/OCR showing the expected result and no popup, black screen, clipping, or wrong account.

If any identity or read-back gate is missing, report `BLOCKED` with the actual error and evidence path. Never infer success.

## Recovery sequence

1. **Classify the failure.** Separate transient transport/ATX/session errors from identity or UI-state errors. `UI_DUMP_INVALID` during profile navigation is not proof of a safe target; treat it as a blocked mutation until the screen is captured and inspected.
2. **Inspect O(1).** For machine `N`, run `python D:/Taadaa/tools/inspect_machine.py N`. Record serial, focus, screen state, battery, Wi-Fi and proxy. Do not broad-scan the farm.
3. **Capture before cleanup or retry.** Acquire the device lock, capture the current screen, run WinRT OCR, and inspect the screenshot visually. If focus is `SplashActivity`, feed, a public profile, another account, or an unknown surface, do not tap through it.
4. **Use ATX session capture as the primary UI XML route.** Construct `AdbClient(adb_path=ADB_BIN, serial=serial)` and call `capture_atx_session_ui(...)`. The persistent ATX session route can return `VERIFIED_XML` even when direct device-local `/dumpUI` returns 404. Do not silently downgrade to shell UiAutomator dumping on S7/Android 7/8.
- Bound recovery. If the exact target can still be safely re-verified, allow one code-level recovery such as ATX session rediscovery/reset or adapter settling retry (up to 3 attempts with 1.0s delay checking `xml.lstrip().startswith(("<", "<?xml"))`), then one bounded retry.
- Preempt stale device locks safely. For operator-driven CLI mutations on single machines, use `operator_device_lock(machine=N, serial=serial, force_preempt=True, timeout=30.0)` to reclaim orphaned locks left by timed-out or aborted runs.
- Continuous user transparency during background runs. When dispatching workers or running bounded live interactions (>30s) in the background, send an immediate checkpoint status message before handing control to the background runner so the user is never left wondering if the coordinator is frozen.
- Fail closed. If XML remains invalid, account identity is unknown, or the runner reaches its retry bound, stop the mutation and preserve the failure screenshot/OCR/log.
7. **Verify post-action.** Re-dump the profile through ATX, parse the exact target account, verify the mutation marker/state, and capture a fresh screenshot for vision inspection. Only then report success.

## Evidence rules

- Keep failure and success screenshots separate and use absolute paths.
- Inspect a screenshot before attaching `MEDIA:`; confirm the intended Profile/Switcher, expected new content, and absence of visual defects.
- Report the exact exception, not a vague “automation failed.”
- Do not attach old screenshots or reuse prior session evidence.

## Farm safety pitfalls

- Never treat `dry_run=True` as a live canary.
- Never mutate while the app is on a different public profile or while `SplashActivity` is still active.
- Never use direct ADB input commands as an emergency way through an error screen.
- Never change account/workbook/queue state to `DONE` before real-device read-back.
- Do not write a skill entry describing an unvalidated worker patch as a reliable fix.
- S7 Profile Screen Edit Entrypoint: Never tap imaginary coordinates (e.g. `(870, 558)`) or abort when text button 'Sửa hồ sơ' is absent in OCR; on Samsung S7 (1080x1920) newer TikTok UI, the canonical entrypoint to enter `EDIT_PROFILE` is the toolbar pencil icon at `(72, 148)` (x: 50–90, y: 130–170).
- Bio-less Profile Variant (+ Thêm tiểu sử vs Find Friends Trap): On accounts with no bio yet, TikTok displays a centered `+ Thêm tiểu sử` button (Y ≈ 840–890) instead of 'Sửa hồ sơ', and the top-left toolbar `(72, 148)` becomes the 'Find Friends' icon rather than a pencil. If tapped, it enters a ping-pong loop between Feed and Find Friends until max steps. Always match `(sua|chinh sua|edit)\s*(h[o0]|profile)` OR `\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su` dynamically via OCR before falling back to fixed pencil coordinates.
- Watchdog Re-queue Contract: Only verified accounts with valid proof PNG are committed to state JSON. Failed runs (exit_1, exit_2, max steps) must never write cooldown state, ensuring they are automatically re-queued in subsequent 15-minute watchdog cycles.
- Cold-boot Splash Tolerance: Never trip `MAX_SAME_STATE` aborts on `SplashActivity` / minimal text (`len(lines) <= 3`) during app launch; 4G proxies take 25–35s to load. Expand splash tolerance to 8 steps (~35–40s) and avoid pressing `BACK` during splash.

## Avatar-specific semantic gate

Mechanical upload success is not semantic asset success. Before changing an avatar, open and inspect the exact resolved source file used by the runner; never trust a proposal canvas label, filename, folder number, or prior description. Bind `target account -> source folder -> exact avatar path` before upload, then bind the same account to a fresh Profile screenshot after upload. A successful push, crop-save, `exit=0`, `verified=True`, `FORCED_REPLACED_VERIFIED`, or workbook `Avatar = OK` proves only the mechanical flow. It does not prove that the intended image was selected.

Verify profile fields independently: a Bio can be confirmed while the Avatar is wrong or unproven. Report `Bio: confirmed` and `Avatar: incorrect/unproven` separately. If source and post-action semantics disagree, report `BLOCKED` or `UNPROVEN` and do not treat the workbook flag as final. See `references/avatar-source-semantic-verification-20261020.md`.

## Supporting detail

See `references/live-profile-mutation-atx-recovery-20261020.md` for the validated ATX-vs-direct-`/dumpUI` observation, evidence sequence, and exact failed-live-run signature from a real machine.
See `references/avatar-source-semantic-verification-20261020.md` for the avatar-specific source-asset gate and the false-success pattern where the runner uploaded a canopy image while the proposal described a cat.
See `references/tiktok-s7-profile-edit-pencil-coordinates-20261020.md` for the Samsung S7 Profile toolbar pencil icon coordinate invariant `(72, 148)` and root-cause analysis of the 5-step PROFILE loop abort.
See `references/tiktok-profile-no-bio-add-bio-button-variant-20261021.md` for the bio-less Profile variant (`+ Thêm tiểu sử` vs Find Friends trap) and dynamic button resolution.
See `references/cold-boot-splash-loading-tolerance-20261021.md` for the 4G proxy cold-boot splash loading tolerance invariant and prevention of premature UNKNOWN exit_2 aborts.
