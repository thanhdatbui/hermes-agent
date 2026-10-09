# Partial fallback canary and closeout remediation

## Changed-behavior canary

A navigation-only hook such as `nav_search` proves startup and routing, not the follow-engine change. For Mode 2 partial-follow fallback, use the real Mode 2 path with a bounded/mock or explicitly approved live run. Require result evidence for:

- `mode2_followed_count`
- `mode1_followed_count`
- total `followed_count`
- `follow_failed`

Do not treat `status=OK` alone as proof. If `FOLLOW_FAILED` appears, stop immediately and do not fallback to Module 1.

Before a live canary, select only a row with `follow_failed=false` and no active cooldown; re-check after the run. A previously healthy row can become quarantined during the canary.

## Legacy cooldown migration review checklist

- Parse the complete legacy date strictly as `%Y-%m-%d`; never use `[:10]` or permissive prefix matching.
- Suffixes and garbage such as `2026-08-27-corrupt` and `2020-01-01junk` must remain fail-closed.
- On expiry, remove all legacy date/cooldown markers so repeated reads do not re-migrate, rewrite state, or duplicate expiry logs.
- Add tests for malformed suffixes and repeated reads after expiry.
- Normalize the test file's line endings before review; verify `git diff --numstat` reflects only intended test additions.
- Run the focused state tests and the relevant regression set; then run closeout against the exact changed commit and target files. A timeout or unavailable reviewer is not an approval.
