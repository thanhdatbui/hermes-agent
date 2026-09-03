# 9Router Direct API Auth & Review Timeout Notes

## 1. HTTP 401 Unauthorized on Direct Python / curl calls
Direct HTTP calls to `http://127.0.0.1:20128/v1/chat/completions` fail with `401 Unauthorized` if the `Authorization: Bearer <key>` header is omitted.
- The active API key is stored in `$LOCALAPPDATA/hermes/.env` (or `C:\Users\Kibe\AppData\Local\hermes\.env`) as `NINEROUTER_API_KEY=sk-...`.
- When writing ad-hoc python scripts to call 9Router HTTP API, always parse `.env` to retrieve `NINEROUTER_API_KEY`.

## 2. Review Timeout on Large Diffs (Sol / Opus)
- High-reasoning models like `gpt-5.6-sol` (`plan-review-hard`) and Claude Opus on large git diffs (>30KB) can take 5 to 10 minutes (>300s to ~600s) to produce full code-review output.
- Direct `urllib` / `requests` synchronous calls with standard 300s timeout will hit a client-side timeout while 9Router is still generating.
- Recommended pattern:
  - Set request timeout to `900` seconds.
  - Launch via a background runner script with `terminal(background=True, notify_on_complete=True)` and poll / wait on completion.
