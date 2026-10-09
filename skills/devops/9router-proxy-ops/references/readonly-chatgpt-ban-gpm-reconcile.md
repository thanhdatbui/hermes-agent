# Read-only OmniRoute ChatGPT-web ban audit

Use this procedure when the operator asks for a current inventory of banned ChatGPT Web accounts without opening profiles or logging in.

## Source APIs

- OmniRoute management API: `GET http://127.0.0.1:20129/api/providers`
- Optional health checkpoint: `GET http://127.0.0.1:20129/api/health`
- GPMLogin v3 inventory API: `GET http://127.0.0.1:19995/api/v3/profiles`

These are read-only calls. Do not call provider test, update, delete, start-profile, browser, OAuth, or login endpoints for this audit.

## Classification

1. Parse only connections where `provider == "chatgpt-web"`.
2. Flag a connection if **any** of these is true:
   - `testStatus == "banned"`
   - `errorCode == "403"` (compare as a string after normalization)
   - `lastError` contains the case-insensitive Sentinel marker.
3. Preserve the raw `lastError`, `lastErrorAt`, `lastTested`, `errorCode`, `lastErrorType`, `id`, `name`, `priority`, and `isActive` fields in the evidence record.
4. Do not classify an inactive account as banned unless one of the explicit ban predicates is present. Inactive alone is not evidence of a ban.

## GPM reconciliation

Extract the email from the OmniRoute display name before the first parenthetical suffix, then compare case-insensitively against GPM profile inventory names. Report exact matches only; do not infer a profile from priority, ordering, proxy port, or a partial username. For matched profiles, report only non-secret identifiers such as profile ID, name, group ID, and profile path if needed.

A zero-match result is a valid finding: report that the current GPM inventory does not contain the OmniRoute email, rather than opening profiles to investigate.

## Redaction and report gate

- Never print `apiKey`, cookies, bearer tokens, raw proxy credentials, or full secret-bearing provider-specific data.
- Include the exact error sentence and timestamps, but redact any secret-like substrings if present.
- Report totals for: all `chatgpt-web`, explicitly banned, active, and inactive-but-not-banned.
- State the API observation timestamp and the fact that no profile was opened or login was attempted.
- Keep the final table complete: one row per flagged connection, including connection ID and GPM mapping status.

## Common trap

`/api/providers` may contain a large mixed-provider response and the GPM inventory may contain unrelated Hotmail/Gmail profiles. Do not treat the presence of a GPM server response or an unrelated profile as a mapping. Use exact email reconciliation and keep `unmatched` distinct from `not banned`.
