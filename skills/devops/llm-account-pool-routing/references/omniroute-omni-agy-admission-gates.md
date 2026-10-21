# OmniRoute + AGY Pool Admission Gates

Use this runbook before adding an existing Google/Antigravity account to both OmniRoute and the native AGY CLI pool.

## Verified admission sequence

1. **Inventory both source and target records.** Resolve the account by exact normalized email in the source credential store and in OmniRoute `provider_connections`; record connection IDs, provider, active flag, test status, expiry, project ID, and entitlement metadata. Hash tokens for comparison; never print token material.
2. **Require a live credential, not merely a row.** A source record containing access/refresh tokens is insufficient. Confirm refresh or a provider health/usage probe succeeds and that the target connection is not `expired`/401. If the target is stale, do not add it to a routing combo or copy it into an AGY sandbox.
3. **Require entitlement before Pro-pool admission.** Accept only an explicit Pro entitlement such as `tier=g1-pro-tier` / `subscriptionTier=Google AI Pro`; keep Free/unknown accounts out of Pro combos.
4. **Require deterministic proxy ownership.** Resolve the account's GPM profile or other source-of-truth mapping to an exact host:port. Confirm that endpoint exists and is active in `proxy_registry`, then confirm an `account`-scope row exists in `proxy_assignments`. `proxy_enabled=1` alone is not evidence of proxy routing.
5. **Stage then activate.** Insert or update the connection inactive, create the exact proxy assignment, verify it, and only then activate the connection and add it to the combo. If any gate fails, leave the account inactive/unlisted and report the missing evidence.
6. **Native AGY sandbox admission is separate.** Create one sandbox with a unique installation ID and isolated `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, and `.gemini` state. Verify the email in that sandbox's `google_accounts.json`; do not repurpose the host account (`acc_01`) as a pool member.
7. **Post-change verification.** Re-read the combo membership, connection status, account proxy assignment, and AGY profile inventory. Run one pinned/offline or low-risk canary only after all gates pass; a healthy unrelated pool response does not prove the new account works.

## Fail-closed evidence format

Report each requested account as `READY`, `BLOCKED`, or `NOT_FOUND`, with: source record, target connection ID, entitlement, proxy mapping, token/health result, and exact blocking evidence. Never claim "loaded", "active", or "in progress" without a verifiable database/API result or an active process handle.

## Session lesson

A pair of accounts can simultaneously have valid-looking source records and Pro metadata while OmniRoute still reports `expired`/401 and has no account proxy assignment. Treat that combination as **blocked**, not as a partial success. Ask for the exact GPM profile ID or proxy port only when it is the missing source-of-truth mapping; do not guess a port from pool order.
