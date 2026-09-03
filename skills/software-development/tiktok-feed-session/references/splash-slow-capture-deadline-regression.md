# Splash-slow capture deadline regression

## Trigger

Use this pattern when an old TikTok device (notably Samsung SM-G930F) reports `capture_deadline_exceeded` immediately after launch even though the feed is visually rendered. The usual evidence is TikTok still focused with `SplashActivity`, followed by a valid feed capture once the splash settles.

## Consumer-local recovery pattern

1. Raise the lightweight consumer capture deadline cap conservatively (8s → 20s, or a config-bounded equivalent) in the consumer capture contract. Do not modify `automation-core` for a feed-session policy fix.
2. In the feed capture seam, handle `capture_deadline_exceeded` before the generic force-stop/reboot/coordinate ladder:
   - wait non-destructively for a bounded 30–60s budget (default 45s, configurable);
   - poll focused package/activity and require `com.ss.android.ugc.trill` with no `SplashActivity`, then recapture;
   - accept the retry when the XML is valid (and let normal feed classification decide the row result);
   - record redacted structured wait/recapture evidence in the attempt list and log.
3. If the wait/recapture budget is exhausted, fall through to the existing ladder unchanged. Do not consume or reset the B2/B3 one-per-turn/per-machine budgets. Keep coordinate fallback evidence-gated and preserve `MANUAL_REVIEW`/manual-needed when all safe paths are exhausted.

The handler must be bounded and non-destructive: no blind tap, no extra relaunch, no reboot, and no bypass of sensitive-screen fail-closed guards.

## Regression-test contract

A test that only asserts “capture called twice and final row is feed” is insufficient: an older generic retry may already do that. Use a sequence fixture (deadline terminal → post-splash feed XML), assert a handler-owned marker or structured event such as `splash_slow_capture_recovered`, assert the force-stop/coordinate ladder was not entered, and retain a separate exhaustion test proving the existing ladder/manual review path still runs.

## Verification gate

Run the focused regression first, then the related feed/capture suites, `py_compile` for every changed Python file, and `git diff --check`. Re-read the modified regions and inspect the final diff before reporting completion. If a broader suite has an unrelated pre-existing failure, report its exact test and assertion separately; do not weaken the regression or change unrelated production behavior just to make the suite green.
