# GPM Pure Login Session Persistence & Closeout Lessons (2026-10-21)

## Verified architecture
- For `--login-only`, start the profile through GPM Local API v3: `GET /api/v3/profiles/start/{profile_id}?skip_proxy_check=true`.
- Read `data.remote_debugging_address`, then attach Playwright with `connect_over_cdp("http://<address>")`; do not pass a separate Playwright proxy. The GPM profile owns proxy, fingerprint, cookies, and browser lifecycle.
- Close the CDP connection and call `/api/v3/profiles/stop/{profile_id}` after the page work. A `login_only_success` event during one browser run is not proof of persistence; restart the same profile through GPM API/CDP and verify the authenticated URL/body/identity again.

## Deterministic profile mapping
- Resolve by an explicit `gpm_profile_id` when available; otherwise paginate `/profiles` and match the email as a whole token in the profile name. Require exactly one match. Zero or duplicate matches must fail closed, not guess by folder or port.
- Farm profile naming `<machine> - <email> - <proxy-port>` is a useful invariant and should be audited directly through the GPM API. Still treat Master Excel as the account source of truth; stale hardcoded `ACCOUNTS` entries can point to deleted/DIE accounts.
- For a DIE account, verify all three surfaces before claiming no live session: Master workbook status/archive, physical profile/cookie storage, and GPM API profile inventory. Remove only stale state/code references after this evidence is collected.

## Closeout and evidence discipline
- Focused mocked tests should cover explicit IDs, paginated single match, zero/duplicate match, start failure/missing CDP address, and stop/cleanup failure. In the observed pipeline this raised the focused suite from 39 to 47 passing tests.
- `NEED_CONTEXT:<path>` from closeout is a payload truncation/context problem, not approval and not a code score. Do not report DONE; either compact the test diff without weakening assertions or use the mandated reviewer handoff. Keep the implementation/test pair within the review payload budget.
- A Canary pass and passing tests do not by themselves satisfy strict closeout. Report the exact reviewer verdict/score and keep the task open until the active closeout policy is satisfied.

## Known pitfall
- Retaining a fallback from GPM CDP to `launch_persistent_context` can mask profile-resolution or GPM-start failures and may apply a derived proxy instead of the profile's configured proxy. Use it only when the contract explicitly permits offline/test compatibility; production paths should emit fail-closed telemetry for GPM start/CDP failures.
