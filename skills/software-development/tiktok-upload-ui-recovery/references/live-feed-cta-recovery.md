# Live feed CTA recovery — evidence from 2026-08-09

## Observed run

Target scope: machines 1 and 20 in `tiktok-luot nuoi acc`.

- Preflight XML confirmed both targets had TikTok `Mua ngay` + `Đóng`.
- M1 completed 3/3 feed swipes and released its lock, but prepare/relaunch removed the original CTA before the CTA-specific handler was exercised. Do not call that CTA proof.
- M20 first run stopped before action because UI capture recovery ended with `UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2` and `SHELL_NO_HIERARCHY`; preserve blocker evidence and do not swipe from a splash screenshot.
- M20 targeted retry later captured valid XML, completed 3/3 swipes, then encountered `Mua ngay` with dynamic `Đóng` (`hwh`/`hwn`) at the final popup checkpoint. The log showed `gem_blind_probe success` but no `gem_blind_tap`, and the final XML still contained both CTA nodes. This is an integration failure: detector observation must not be reported as dismissal.

## Required behavior

```text
exact TikTok Mua ngay
  -> one bounded evidence-gated feed swipe
  -> recapture
  -> if Mua ngay remains: detect current close_element and tap that dynamic Đóng
  -> recapture and verify
  -> never tap Mua ngay; never use static hvm/hwh/hwn IDs
```

The availability of `Đóng` is not a precondition for the initial swipe. `Đóng` is fallback-only after recapture.

## UI capture ladder

Use one tier per failure signature, in order:

1. ATX/uiautomator cleanup.
2. One TikTok force-stop + `monkey` relaunch.
3. One authorized and eligible soft reboot, with boot/VPN/readiness/focus gates.
4. After ladder exhaustion, coordinate **swipe only** may be used when screenshot classification proves TikTok For You/feed, portrait/display geometry is known, and no sensitive/system marker is present.

A splash/loading/launcher/unknown screenshot is not evidence for a feed swipe. Screenshot evidence can authorize a low-risk feed swipe, but it cannot prove an exact CTA selector or substitute for post-action XML when dynamic close is required.

## Verification checklist

- Log an explicit `swipe_up_through_overlay` event with handler, coordinates, bounds/geometry, and `max_attempts=1`.
- Log post-swipe recapture artifact and `recapture_verified`.
- If CTA persists, log an explicit `gem_blind_tap`/dynamic-close action with the current XML selector. A detector `probe success` alone is not action proof.
- Report each machine independently. Batch exit code is only an aggregate signal.
- Translate runner status lines into concise Vietnamese user-facing output.
