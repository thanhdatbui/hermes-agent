# Remote OmniRoute admission troubleshooting

## Scope

Use this when Hermes clients share one OmniRoute/OpenAI-compatible proxy and requests intermittently fail with `503 chat_admission_busy`, local `504` queue expiration, or truncated streams.

## Evidence sequence

1. Query the proxy health and catalog endpoints, but do not use catalog success as generation proof:
   - `/api/health`
   - `/v1/models`
2. Read `/api/providers` and `/api/resilience`.
3. Correlate the failure timestamp with the proxy log and the Hermes agent/gateway log.
4. Run one short direct canary and one two-request concurrent canary. The concurrent probe must resemble the real client enough to expose admission pressure (large history and tools when applicable).

## Interpretation

- `503 chat_admission_busy`: local/upstream admission rejected the request at that instant; it is not equivalent to an invalid model ID.
- One active OAuth connection with `maxConcurrent: null` plus a global queue allowing multiple requests is a likely single-account contention path.
- `504` mentioning local queue execution expiration / `maxWaitMs`: the proxy abandoned a queued or delayed request; increasing queue wait can reduce false failures but cannot increase upstream quota.
- `403 with x-goog-user-project` followed by retry without the header: compatibility fallback; investigate persistent failures separately.
- `TruncatedStreamError`: stream transport ended early; correlate with load and retry behavior before declaring the account invalid.

## Safe runtime mitigation

Use official runtime endpoints, not SQLite edits:

```text
PUT /api/providers/<connection-id>
{"maxConcurrent": 1}
```

For local queue expiration, use a partial resilience update that preserves unrelated settings:

```text
PATCH /api/resilience
{"requestQueue":{"maxWaitMs":120000}}
```

Do not increase retry counts as the first response to admission pressure. Do not delete, rotate, or reconnect OAuth credentials unless a fresh provider response proves an authentication/validation failure.

## Verification

Re-read `/api/providers` and `/api/resilience`. Run two concurrent generation requests and require both to return `2xx`; the second request should normally have higher latency when serialization is active. Also verify the connection remains active/healthy and has no new persistent error state. Report the upstream catalog count and picker-level count separately.
