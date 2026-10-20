# On-demand Advisor routing and timeout layering

## Operator decision
The operator approved switching Advisor Sol from automatic post-response append to **explicit on-demand** use. Ordinary questions must not incur a Sol call or latency. Explicit triggers include `gọi advisor`, `hỏi sol`, `gọi sol`, `sol thấy sao`, `nhờ sol review`, and `sol lên plan`.

## Why context enrichment alone did not solve the problem
Hermes already had a briefing pack: recent user/assistant turns, machine/account/serial extraction, redaction-before-clipping, and payload bounds. However, fixed clipping (`280` chars per message and `1,500` chars total) can remove the actual decision rationale. A larger context window is useful only when the call is intentional and topic-scoped; expanding it while auto-appending increases latency and attention drift.

## Timeout layers to keep distinct
When improving Advisor latency, inspect all layers rather than changing only the client:

1. Hermes adapter timeout and transport mode (`advisor_tool.py`); streaming should use first-token, idle-token, and total deadlines.
2. OmniRoute runtime env, loaded at process startup (`STREAM_READINESS_TIMEOUT_MS`, `ACCOUNT_SEMAPHORE_TIMEOUT_MS`); changing `.env` requires an OmniRoute restart before it affects RAM.
3. Upstream/provider waterfall and account rotation; exhausted web-pool accounts can consume time before a healthy account is reached.
4. Foreground terminal/harness limits; long live probes should not be treated as proof that the route is broken.

## Verification contract
For an on-demand change, verify the classifier/dispatch seam offline: ordinary advice does not call Sol; explicit trigger calls it once; the primary response remains intact when Sol is unavailable. Separately verify timeout configuration and process restart state. Do not claim full success from a static `.env` read alone.
