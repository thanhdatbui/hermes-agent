# Profile verification anchor and preserve-scene pattern

## Problem pattern
A feed session taps the Profile bottom tab, then reports `profile account mismatch`. The artifact may show a value such as `Message` as `display_name`, followed later by Android Launcher/Home. These are two separate questions:

- Was the account identity actually verified?
- Which component moved the device to Home after the failure?

Do not infer either answer from the first text node or from the terminal Home screenshot.

## Correct parser contract
- Parse XML into UI elements and exclude SystemUI nodes.
- Confirm the selected bottom navigation marker is Profile (`Hồ sơ` or `Profile`) before identity matching.
- Locate the `@username` node and a profile-specific display-name/anchor node. `texts[0]` is never a valid display-name selector.
- If the username anchor is absent, return empty identity fields and fail closed; do not copy arbitrary labels such as `Message`, `Hộp thư`, or `For You` into `display_name`.
- Normalize the expected account and candidate username consistently, including one leading `@` removal, but only after the screen/anchor contract is satisfied.

## Bounded lag retry
Use a small, explicit retry ladder: capture → wait → recapture; if the Profile header is scrolled out, perform the existing bounded scroll-up recovery and recapture. If navigation itself is suspect, one bounded re-tap may be used only under a specific marker/selector rule. Every successful-match fixture must contain valid Profile evidence, not merely an `@username` string.

## Preserve-scene boundary
When the mismatch is terminal:

- Keep `_cleanup_close_all_on_error` disabled / preserve-blocker-screen active.
- Do not add a fallback Home, BACK, force-stop, or generic cleanup in the verifier.
- Read target-scoped JSONL and manifest to prove whether in-flow cleanup was skipped.
- Search independent actors (TTL/dead-owner reaper, hard-stop recovery, wrapper finalizer, timeout hooks) for `keyevent 3`, `KEYCODE_HOME`, or force-stop and correlate their timestamps with lock ownership/TTL.
- Classify candidates as confirmed, excluded, or unproven. Report the mismatch and terminal state separately.

## Minimal regression matrix
1. XML has `Message` as an early text and a selected Profile marker but no username: mismatch; `profile_display_name` and `profile_username` remain empty/null.
2. First capture is a loading Profile screen; second capture includes selected Profile plus the expected username: matched.
3. XML contains the expected `@username` but no Profile marker: fail closed unless a separately tested profile-anchor rule proves the screen.
4. Mismatch artifact has `cleanup_close_all=skipped` and `preserve_blocker_screen=true`: verifier does not emit Home/force-stop.

Keep account identifiers and credentials out of fixtures and references; use synthetic placeholders.
