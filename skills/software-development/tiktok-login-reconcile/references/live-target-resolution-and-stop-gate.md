# Live target resolution and STOP-GATE evidence

Use this reference for any multi-device TikTok reconcile/login incident where the user names machine numbers.

## Exact-target procedure

1. Resolve each machine number through the canonical workbook/device-map source. Record `machine -> serial`; never use `adb devices` ordering, stale incident notes, or guessed filenames as mapping.
2. Confirm only those serials are online. Keep the requested target set exact; do not include neighboring machines.
3. Capture each target independently before any state-changing action:
   - screenshot from the target serial;
   - foreground/resumed activity and focused window;
   - bounded power/keyguard and VPN state when relevant;
   - UI XML only when the dump succeeds and the file is actually present.
4. Store an evidence manifest containing machine, serial, timestamp, paths, command return codes, and the observed activity/focus.
5. Compare fresh state with the reported failure. Mark the report `confirmed` only when the exact failed-attempt artifact supports it. If the current state differs, mark the original failure `UNPROVEN` and preserve the scene.
6. Under the live STOP GATE, ask for authorization before force-stop, relaunch, reboot, tap, retry, or recovery—even if the user previously said “handle both” but did not authorize a specific state-changing step after fresh evidence contradicted the report.

## Capture failure handling

A failed UI dump is not proof of a particular screen. Use activity/window/power diagnostics as bounded classification evidence, retain the matching screenshot, and report the XML artifact as missing/incomplete. Do not compensate by repeatedly dumping, blindly relaunching, or reading a stale XML path.

## Report shape

- `Mục đích`
- `Kết quả` per machine
- `Bằng chứng`: machine, serial, timestamp, screenshot/XML/log path, observed activity
- `Confirmed / Excluded / Unproven`
- `Blocker / authorization needed`

Keep the report concise and send actual screenshot media when the platform supports it; do not present a path as if it were visual proof.
