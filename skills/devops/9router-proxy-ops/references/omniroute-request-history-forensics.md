# OmniRoute request-history forensics

Use this for a read-only investigation of provider-specific traffic around a 403/429 incident.

## Targeted workflow

1. Confirm the runtime and health without changing state:
   - OmniRoute is normally `127.0.0.1:20129`.
   - `GET /api/health` and `GET /api/monitoring/health` are safe health checks.
2. Inspect the known local storage read-only:
   - `C:\Users\Kibe\AppData\Roaming\omniroute\storage.sqlite`
   - Relevant tables include `call_logs`, `request_detail_logs`, `usage_history`, `proxy_logs`, `audit_log`.
   - Prefer Python `sqlite3` opened with `file:<path>?mode=ro`; do not write, vacuum, checkpoint, or copy/repair the live DB during an incident review.
3. Probe only known read endpoints, using the exact provider connection IDs and the requested UTC window:
   - `/api/tools/traffic-inspector/requests`
   - `/api/usage/requests-by-provider-date`
   - `/api/usage/history`
   Treat query parameters as endpoint-specific; a route may ignore `providerId`, `from`, or `to`.
4. Query provider metadata with `GET /api/providers/<id>` only if needed. Redact API keys, cookies, emails, tokens, and full session identifiers in output.

## Interpretation rules

- `traffic-inspector/requests` is the strongest source for request-level timestamp/status/session/IP/concurrency evidence. An empty result is evidence of no retained inspector rows, not proof that no traffic occurred.
- `call_logs` and `request_detail_logs` may be empty even when provider metadata records a 403. Check table counts and min/max timestamps before concluding.
- `requests-by-provider-date` may return logical-provider/day aggregates rather than connection-level or time-window data. Do not attribute those totals to a specific provider ID unless the response/schema proves that mapping.
- `usage/history` is an aggregate and may ignore the supplied provider ID/window. Verify response semantics and storage date range.
- Provider metadata fields such as `lastTested`, `lastErrorAt`, `testStatus`, and `errorCode` establish an observed failure event, but not request volume or spam.
- `consecutiveUseCount=0` does not prove absence of earlier traffic; conversely, a logical provider's large aggregate total does not prove either target connection generated it.

## Reporting

Report per target ID: request count (or unavailable), exact timestamps, status, concurrency, session/IP (or unavailable), source/endpoint, and redaction. Explicitly separate observed facts from missing-retention limitations. Conclude `evidence of spam`, `no evidence of spam`, or `inconclusive`; when request-level history is absent, the correct conclusion is normally **inconclusive / no evidence in retained logs**, not a definitive clean bill of health.

Never call a provider test, open a GPM profile, modify provider state, or mutate the database for this investigation.
