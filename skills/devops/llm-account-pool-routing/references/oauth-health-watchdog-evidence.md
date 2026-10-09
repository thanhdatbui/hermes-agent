# OAuth Health Watchdog Evidence

## Health semantics

Keep these states separate:

- **Token/session validation** (for example `/api/providers/validate`) proves only that the credential/session is accepted by the validation endpoint; it does not prove a real model completion succeeds.
- **Completion health** requires observed production traffic through the model route. Do not add quota-consuming probes when the requested operation is read-only.
- **Unknown** means no reliable evidence has been recorded. Empty `apiKeyHealth` or absent completion telemetry is not evidence of death.
- **OAuth revoked/invalid** can be auto-disabled only with unambiguous recorded evidence: HTTP/error code 401, `upstream_auth_error`, or a provider message explicitly stating token invalid/revoked.

## Watchdog contract

1. Inspect the scheduler and deployed script first. Extend an existing provider watchdog rather than creating a duplicate cron.
2. For Codex OAuth pools, consume recorded traffic/error state only. Never bulk-call `/test` or model completion to classify unknown accounts.
3. Auto-disable only `isActive=true` connections after re-checking the backing-store provider identity. Preserve user-disabled/Standby accounts.
4. Keep unknown, quota, rate-limit, timeout, expired-but-unconfirmed, and ambiguous failures active; report them for later observation.
5. Emit an audit record containing account identity and exact evidence category/reason for every automatic disable.

## Offline verification matrix

Use a focused mock/temporary SQLite regression, with no network, ADB, or live model calls:

- hard 401 evidence -> disables the Codex row;
- `upstream_auth_error` or explicit token revoked -> disables the Codex row;
- unknown, quota, rate-limit, timeout, and unconfirmed expiry -> leaves the row active;
- `isActive=false`/Standby -> untouched;
- provider guard rejects a non-Codex row -> no mutation.

Then run `py_compile` on the deployed script. Report the exact commands and outputs; do not claim completion health from validation-only evidence.
