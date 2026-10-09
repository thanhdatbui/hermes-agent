# OAuth import, pool routing, and GPM identity

## OAuth is not model-health proof

Treat OAuth reauthentication and model verification as separate gates. After importing a token, verify the intended provider (`codex`), exact connection ID, and canonical Codex model. A request that reports `openrouter/openai/...` is a route/fallback failure, not evidence about Codex OAuth or quota. Do not classify the account from that response.

When reauth creates a new connection, add/update it in the intended Codex combo before testing, or use a provider-pinned request whose response proves the Codex provider and connection. Do not use generic names such as `gpt-5.5` or `gpt-5.6-luna` when routing may fall back. Use the pool's canonical model (for example `codex/gpt-5.6-luna-medium`), explicit connection headers, and require HTTP 200 plus an expected marker. Keep 401/revoked, 402 upstream credits, quota/rate-limit, and route mismatch distinct.

## GPM pagination and duplicate identity

`/profiles` is paginated even when `data` is a list. Read `pagination.total_page` and `pagination.total`; fetch every declared page and fail closed on missing/changed pagination, empty middle pages, or count mismatch. Never conclude no profile from page 1 and never silently overwrite duplicate Gmail keys. Retain all candidates and log ID, profile path, group, and creation time.

For duplicate Gmail profiles, inspect the live session identity in each candidate (Gmail inbox title or ChatGPT session email). If identity remains ambiguous, report `AMBIGUOUS_GPM_PROFILE` and do not start/import/delete arbitrarily. Deletion requires fresh exact-account live proof and stopping the old profile first.

## Evidence pattern from the incident

A generic post-import ping used `gpt-5.5` and returned `402 Insufficient credits` from `openrouter/openai/gpt-5.5`; this did not prove Codex quota exhaustion. The same account passed when tested through the existing Codex pool using `codex/gpt-5.6-luna-medium` and the exact pool connection, returning HTTP 200 with the expected marker. Treat the route prefix as mandatory evidence.
