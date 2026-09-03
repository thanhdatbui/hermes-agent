# Alert trigger vs terminal state

## Why this matters
A farm alert can preserve the classifier reason while the attached screenshot is captured later, after cleanup or focus loss. Treating the two as the same observation creates false claims such as “Captcha is still on screen” when the device is actually at Android Home.

## Evidence contract
For each alert, keep three distinct observations:

1. **Detection evidence** — raw XML/screenshot/focus from the exact step where the classifier produced the reason.
2. **Post-detection action** — force-stop, HOME, cleanup, popup dismiss, retry, or worker exit, including whether TikTok remained foreground.
3. **Terminal evidence** — final screenshot/XML/focus attached to the alert.

Use explicit fields when possible:

```text
trigger_reason=verification marker detected
trigger_screen=manual-needed:verification  # only if detection artifact proves it
terminal_state=launcher                   # if final focus/screenshot is Android Home
terminal_focus=com.sec.android.app.launcher
root_cause_status=unconfirmed
```

## Classification rules
- `trigger_reason=verification marker detected` means the safety/classifier layer emitted that label. It is not proof that the marker survived until terminal capture.
- Terminal Home/Launcher means `focus_lost_after_detection` unless a more specific log proves crash, force-stop, or cleanup as the cause.
- Do not infer VPN/proxy failure from a VPN/key/status-bar icon alone. Require network/focus/log evidence.
- If the only available artifact is a Home screenshot, state the limitation: the original verification UI cannot be reconstructed from that image.
- “TikTok crashed”, “worker force-stopped TikTok”, and “cleanup returned Home” are separate hypotheses; keep them separate until logs or intermediate captures distinguish them.

## Minimal investigation sequence
1. Locate the original alert image and its exact mtime.
2. Find the same target’s detection artifact by machine + run/account identity, not by filename substring alone.
3. Read the nearest XML/focus/log around the detection timestamp.
4. Inspect post-detection actions and the final focus/activity.
5. Report trigger, terminal state, confirmed cause, and remaining hypothesis separately.

## Reporting template

```text
[MÁY XX]
- Trigger: <classifier/safety reason>
- Detection proof: <XML/screenshot/focus path or “missing”>
- Terminal: <screen + focus package/activity>
- Confirmed cause: <only what logs prove>
- Hypothesis: <clearly labeled, or none>
- Blocker: <missing artifact / lock / authorization>
```

Never call a marker “currently visible” when only the terminal Home screenshot is available.
