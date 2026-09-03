# Machine 9 reconcile / watcher lessons — 2026-07-29

## Device information
- Model: SM-G930W8 (`heroltebmc`)
- Serial: `988627414444594c51`
- TikTok: 44.2.3 (`versionCode=440203`)
- Resolution: 1080x1920

## Durable findings

- `detect_feed_controls` can vary with feed content. `bottom_navigation_point(..., "profile")` may still detect the nav point, but core/semantic navigation remains primary.
- The canonical account-switcher flow owns Profile positioning, required scrolling, sticky identity-header selection, and switcher proof. A manual tap that happens to open the sheet is not a replacement contract.
- Reconcile repeatedly rebooted because `_collect_with_recovery` treated Profile/switcher errors as device-reboot signatures. Correct recovery is two bounded app-level inventory attempts; dedicated recovery owns device reboot.
- After reboot, watcher processes existed but there was no fresh machine-9 artifact for the current boot and no live `tun0`. Old `verified.json` artifacts are not current evidence.
- Scheduled task `\TikTokProxyWatcher` appeared Disabled while two watcher parent processes were actually alive. Always inspect the full evidence chain.
- Stale reconcile lock referenced dead PID `43168`; verify PID death before removing stale lock.
- `DONE: result=...` did not mean success; JSON outcomes included `recovery`, VPN timeout, and `ACCOUNT_MISSING`.

## Correct evidence ladder

1. Confirm device boot ID/time and online state.
2. Inspect machine/serial lock and owner PID.
3. Confirm watcher process tree with exact mapping/runtime args.
4. Find a fresh target-specific artifact newer than the reboot.
5. Verify live `tun0` and Android VPN connectivity.
6. Only then start reconcile; read the JSON per-target outcome after `DONE`.

## UI/startup compatibility learned

- Fresh/data-cleared TikTok can show `UniversalPopupActivity` consent; detect by activity signature, use the documented bounded action, and verify dismissal.
- Google Play can interpose `TosActivity` or `PlayCoreAcquisitionActivity`; detect package/activity before applying a bounded fallback.
- UiAutomator can hang on this Samsung variant; prefer activity-state evidence in loops, but retain XML proof where the contract requires switcher verification.
- AdbKeyboard broadcast may time out even when text enters. Never assume field focus; verify each username/password screen transition before entering the next secret.

## Working manual diagnostic flow (not the primary automation contract)

```text
Profile tab -> sticky profile identity header -> account switcher
-> Add account -> signup landing -> "Already have an account? Log in"
-> phone/email/username -> Email tab -> identifier -> password
```

Coordinates observed at 1080x1920 are diagnostic fallbacks only. Core/semantic/image paths remain primary and every fallback requires post-action proof.

## User corrections encoded

- Do not reboot from reconcile by improvisation; follow `docs/ui-compatibility.md`.
- Do not replace image/core navigation with coordinate-only behavior.
- Do not kill/restart live processes repeatedly without a classified failure.
- Every UI/navigation/VPN fix must update `docs/ui-compatibility.md` and applicable tests.
