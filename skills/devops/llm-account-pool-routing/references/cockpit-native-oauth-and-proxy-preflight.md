# Cockpit Codex: native OAuth and proxy preflight

## Purpose

Use this note when operating a Cockpit Tools Codex account pool or wiring it as a local fallback. It records the validated boundaries from a Windows Cockpit Tools 1.3.x session; it is a preflight/canary guide, not a claim that bulk OAuth has been validated.

## Hard boundary

- Do not treat edits to `~/.antigravity_cockpit/codex_accounts.json`, sidecar `manifest.json`, `config.json`, or hand-created auth files as OAuth. Cockpit may show an account while the sidecar still reports `auth_not_found` and routes zero candidates.
- Do not report a batch as successful from account files, a stale quota snapshot, or a green UI card alone. Require a native Cockpit account record, sidecar pool visibility, a live proxy check, and one real API canary.
- Never print access tokens, refresh tokens, API keys, passwords, or proxy credentials in reports. Redact all secrets.

## Safe sequence for a destructive reset + refill

1. Read-only inventory first: count managed Codex accounts, sidecar account IDs, client keys, and API-service state. Record the exact backup target.
2. Create a full backup outside the active tree before removing anything.
3. Clear old accounts through Cockpit's native account-management path (or a documented native API), not by editing only one cache/config file. Restart Cockpit/sidecar and verify the old pool is gone.
4. Pick one GPM profile as a canary. Verify its profile ID, current session, and assigned proxy. Do not launch a ten-profile batch yet.
5. Run the native Cockpit OAuth flow for that profile. Keep the profile-to-proxy mapping explicit and immutable for the canary.
6. In Cockpit, verify the account card is present, shows the expected plan/status, and use the account's native Proxy control. A global API proxy is not proof of per-account egress isolation.
7. Test the assigned egress proxy and confirm the upstream request uses it. A direct upstream probe through the proxy is useful, but it does not replace Cockpit's own account/egress test.
8. Start/restart the API sidecar from Cockpit. Verify `/v1/models` with the redacted client key, then make one minimal mocked/safe text request. Acceptance is an actual successful response, not HTTP listener readiness.
9. Only after the canary passes should the same native flow be expanded, sequentially, to the remaining profiles. Stop on the first repeated auth, proxy, or checkpoint failure; do not fire-and-forget retries.

## Evidence checklist

- Backup path and pre/post managed-account counts.
- Cockpit UI screenshot at each state-changing UI checkpoint: after OAuth form/session is ready, after submit/callback, after proxy assignment, and after API test result.
- Sidecar log line showing account-pool load without `auth_not_found`, `PROXY_ENGINE_MISSING`, or zero candidates.
- `/v1/models` response and one canary completion response with secrets removed.
- Explicit mapping table: profile ID -> account email (masked) -> proxy host/port (credentials masked) -> canary result.

## Failure interpretation

- `PROXY_ENGINE_MISSING` means the proxy engine prerequisite is unavailable; do not proceed with a multi-account OAuth batch or claim per-account proxy safety.
- `auth_not_found` with `candidates=0` after hand-written auth/config files means the files are not the native pool source or the sidecar did not ingest them. Restore from the backup if the active state was damaged, then use native Cockpit OAuth/import.
- A listener on port 60818 only proves the HTTP process is bound. It does not prove account authorization, proxy routing, quota, or completion capability.
- `restrictFreeAccounts=false` is necessary for free-account use when that policy exists, but it is not sufficient evidence that a free account is authenticated or routable.

## What is not validated here

This session did not complete a working ten-profile native OAuth batch. Do not promote the manual token/file injection attempts to a recipe. The durable lesson is the native-flow requirement and the canary/evidence gates above.
