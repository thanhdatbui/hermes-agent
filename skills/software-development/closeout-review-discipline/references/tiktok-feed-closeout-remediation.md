# Focused TikTok feed closeout remediation

Use this pattern when a Taadaa feed-session task arrives with an exact production/test allowlist, a reviewer score just below threshold, and a mandatory focused pytest command.

## Acceptance pattern

1. Treat the user-supplied allowlist and exact test command as hard contract. Inspect only those files plus the minimum call-site/registry seam needed to understand behavior.
2. Snapshot `git status` first. Existing edits inside the allowlist are not automatically yours; inspect the diff and preserve unrelated/untracked paths (for example generated `MagicMock/` artifacts). Never reset, restore, or clean the workspace just to make the closeout diff look smaller.
3. Re-read the live anchor immediately before each write. Large, blank-line-heavy Python flows are vulnerable to fuzzy-patch re-anchoring; after every patch, re-read the changed function and run a syntax/focused check before stacking another edit.
4. After the final edit, run the exact focused command verbatim. Report pytest warnings separately from the real pass count; a passing focused suite is evidence for the current bytes only.

## Three recurring production contracts

### OCR network recovery

An OCR helper must not return an unconditional empty string when XML is unavailable. Split OCR into lines, case-fold each line, drop lines containing SystemUI/status-bar/notification/login noise (`systemui`, battery/charging, notification/thông báo, login/đăng nhập, Google Play, SIM, etc.), and retain clean lines including localized retry/network wording. Test mixed OCR with at least one dropped notification line and one retained retry line, plus an all-noise empty result. If a line contains both exclusion and retry tokens, treat the line as tainted and drop it; package-scoped XML filtering remains the stronger source when available.

### Like-rate telemetry

When computing a valid denominator, use `effective_swipes = swipe_count - already_liked`. Preserve the observed swipe denominator when `already_liked > swipe_count` and emit a structured `LIKE_RATE_TELEMETRY_ANOMALY` warning. Independently warn when `like_count > effective_swipes` while `effective_swipes > 0`; calculate the rate over `effective_swipes`, never `max(like_count, effective_swipes)`, which masks the anomaly as an artificial 100% rate. Regression tests must assert both the denominator and the warning.

### Test-mode upload hooks

Branch on `ctx.mode == "test"` before deriving organic-rest state from account/date/config. Test mode must be explicit and deterministic: log/return the repository's safe skipped/mock payload contract and must not depend on `_is_organic_rest` having been pre-populated. Add a unit test that constructs the smallest context/account and verifies the test-mode result without device, subprocess, or live farm state.

## Evidence boundary

Keep offline focused pytest evidence separate from live farm/canary evidence and from the Closeout Gate score. Do not claim the gate itself passed merely because the named 3-module suite passed; report the exact score/verdict separately when available. Do not commit or push when the task explicitly forbids it.
