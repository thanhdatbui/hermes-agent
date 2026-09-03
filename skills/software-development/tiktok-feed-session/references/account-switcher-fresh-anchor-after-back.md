# Account-switcher fresh-anchor recovery after BACK

## Incident pattern

The feed flow tapped a Profile account-switch anchor, captured Profile again instead of the account-switcher sheet, then used `BACK` and retried the original `UIElement`. The original element can be stale after TikTok re-lays out the Profile header, so the retry may tap the old display-name bounds and end with:

`manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`

The alert screenshot alone does not prove the exact live root cause. Exact `log.jsonl`, `ui.xml`, and matching screenshot remain the authority for live triage.

## Offline reproduction

1. Build an initial Profile XML with a clickable display-name parent at bounds `[20,80][260,135]`.
2. Make the post-BACK Profile XML expose the same semantic header at new bounds `[400,80][700,135]`.
3. Return a valid switcher XML only after the retry tap.
4. Assert the retry sends `input tap 550 107` and never reuses `input tap 140 107`.

This fixture belongs in `python_runner/tests/test_feed_session_smoke.py` and should exercise `_capture_profile_switcher_xml_with_add_phone_guard`, not only the helper that parses an anchor.

## Safe implementation contract

- Keep the existing first capture and typed switcher detection unchanged.
- After the single policy-approved BACK, capture fresh XML.
- If fresh XML is valid Profile, call `_profile_identity_from_xml` and `_find_sticky_profile_header` to resolve the new anchor.
- Do not use a broad text search or guessed coordinate as a replacement.
- Retry once and require fresh switcher evidence; otherwise return the existing manual-needed reason.
- Preserve the original anchor only as a bounded fallback when the fresh capture is absent or malformed; do not treat that fallback as proof of success.

## Verification evidence from the fix session

- Focused regression: `3 passed, 169 deselected` after the new fixture was corrected.
- Full consumer feed-session test: `171 passed, 1 skipped, 4 subtests passed`.
- Account-switcher core tests: `27 passed`.
- `py_compile` and `git diff --check`: pass.
- No live device/ADB action was performed; the Telegram screenshot did not include exact run artifacts, so live root cause remained `UNPROVEN`.
