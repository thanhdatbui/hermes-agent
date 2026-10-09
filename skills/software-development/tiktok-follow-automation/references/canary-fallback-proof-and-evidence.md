# Canary proof: Mode 2 → Mode 1 fallback

## PASS contract

A live canary is **not verified** merely because `mode2_fallback_to_mode1: true` appears. Require all of:

1. `mode2_fallback_to_mode1: true`.
2. `mode1_followed_count > 0`, or an equivalent explicit Mode-1 follow artifact.
3. Fresh full-screen 1080×1920 screenshot captured while TikTok is still on the relevant Search/Profile/Follow screen.
4. State/log readback showing the new follow.

If `mode1_followed_count == 0`, report **NOT VERIFIED**. A Launcher/Home screenshot after teardown proves only cleanup and must never be presented as follow-flow evidence.

## Preflight

Before a live fallback canary, read back the effective config and runtime state:

- `feed_timeout_seconds` must exceed the runner's reserve gate; otherwise Mode 1 may be skipped before it starts.
- Record random session budget, account age/video gate, and current daily budget.
- Confirm Mode 2 ended without `follow_failed` and remaining budget is positive.

## Runtime verification

Verify the actual transition path, not only a flag:

`Mode 2 ended → remaining budget > 0 → Mode 1 invoked → Mode 1 attempted/recorded a follow → pre-teardown TikTok screenshot → state/log readback → cleanup.`

The canary must preserve or expose the pre-cleanup screenshot/artifact. Do not teardown first and then capture Home as evidence.

## Reporting

Use concise evidence-first reporting: PASS/NOT VERIFIED, exact result fields, and the relevant TikTok screenshot. Do not overclaim fallback success when Mode 1 recorded zero follows.
