# Antigravity 403 project-routing diagnosis

## Durable finding

A Gemini request can fail with HTTP `403` even while the Antigravity connection is active, OAuth token refresh succeeds, quota telemetry shows remaining capacity, and periodic connection tests return `200`. Do not classify this as quota exhaustion without a `429` or an explicit quota/exhaustion signal.

## Sanitized evidence pattern

Observed across one active Antigravity connection:

- Requests to `antigravity/gemini-3.7-flash-high` and `antigravity/gemini-3.7-flash-medium` returned `403`.
- The call-log classification was `error_type=project_route_error` and `error_code=upstream_403`.
- The runtime first sent `streamGenerateContent` with `x-goog-user-project`, retried once without that header, and still received `403`.
- The same connection later produced `403` for an Antigravity Claude model, so the failure was not specific to a single Gemini model.
- No tokens were consumed in the failed call artifacts.
- The account remained active; its transient error state was later cleared.
- Later scheduled `connection-test` calls returned `200`; this proves refresh/connectivity, not necessarily chat invocation authorization.

## Safe read-only procedure

1. Check the live listener PID for `20128` and query `/api/health` and `/api/version`.
2. Use the active runtime data directory, not the repository's historical `logs/application/app.log` or a dev checkout log.
3. Read only the newest relevant records from the runtime application log, `call_logs`, `usage_history`, and `provider_connections`.
4. Correlate request time, requested/translated model, status, error type, retry line, connection ID, and post-error state.
5. Check quota state separately. A remaining percentage of `100%` or a successful quota/connection probe is evidence against exhaustion, not evidence that invocation is authorized.
6. If `responseBody` is absent, do not invent the provider's detailed reason. State that the remaining possibilities include project permission, disabled service, stale project binding, geo/policy rejection, or another upstream authorization rule.

## Reporting template

- **Runtime:** listener, health, version/latest.
- **Failure:** UTC timestamp, requested model, translated model, HTTP status, error type/code.
- **Upstream behavior:** retry/header behavior and whether a response body was retained.
- **Account/quota:** active state, token-refresh result, quota evidence; never expose credentials.
- **Conclusion:** project/auth/routing vs quota, with confidence and unresolved detail.
- **No mutation performed:** explicitly say whether restart, OAuth reset, account disable, cooldown clear, or bundle patch was not performed.

## Pitfalls

- Repo logs can be stale while the real runtime has a newer log under `.omniroute`.
- `connection-test=200` is not a chat-generation test.
- A cached quota percentage is not a permission check.
- A `403` should not trigger account banning or auto-disable by itself.
- Do not disclose project IDs, email addresses, tokens, request IDs, or full connection identifiers in user-facing reports unless explicitly required; mask them by default.
