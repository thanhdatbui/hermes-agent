# OmniRoute pool burst notes

## Validated runtime pattern

For a tool-heavy client, do not map one session to one account. Configure a single client-facing combo alias containing the same production model on distinct pinned `connectionId` targets; the client calls the alias and Omni routes each generated request.

Observed OmniRoute v3.8.50 boundaries:

1. Process-wide chat admission runs before account selection. `CHAT_MAX_HEAVY_IN_FLIGHT` and structural `chat_admission_busy` are independent of the number of OAuth connections.
2. Direct `provider/model` selection can concentrate on one account; `maxConcurrent=1` then serializes that selected account and does not by itself spill a queued direct request.
3. Combo dispatch can pre-check pinned targets with `isAccountSemaphoreFull(...)`, mark a full target as `concurrency_cap`, and continue to the next target. This requires real distinct connection targets and a request that reaches combo dispatch.
4. A session is not equivalent to one request. Tool rounds, retries, compression, and handoffs can create many model requests from one session.

## Safe verification

Run both a light and production-shaped heavy burst through the exact combo alias. Record HTTP status, latency, request shape, sanitized selected-connection prefixes, and rejection reason. A light pass does not validate heavy admission. Interpret `structure_limit`/`chat_admission_busy` as pre-routing global admission; `concurrency_cap`/all-targets-skipped as combo capacity; upstream 429/503 as provider-side behavior.

## Capacity tuning lesson

Do not infer that `maxConcurrent=2` is unsafe from one five-session failure, and do not infer that it is safe from one five/six-request pass. First identify whether the burst was concentrated on one account or rejected before routing. `maxConcurrent` is per connection, not per session; one tool-heavy session may emit many model requests through tool rounds, retries, compression, handoffs, or parallel subcalls. An unset/null cap means no explicit cap, not a guessed default such as 10.

When the operator explicitly wants an experiment, honor the requested cap rather than silently forcing 1: preserve a rollback value, set the global heavy-admission ceiling separately, and run a production-shaped heavy burst. For three active accounts, a validated conservative point was `maxConcurrent=1` per account, global heavy admission 3, `OMNIROUTE_CHAT_ADMISSION_HEALTHY_HEADROOM=0`, and a 120-second admission wait. A separate experiment at `maxConcurrent=2` per account with global heavy admission 6 also passed a six-request, 211-message burst in roughly 11–19 seconds after restart. Neither result is universal; both are evidence only for that exact build, pool, admission settings, upstream state, and payload shape. Do not equate this pool strategy with round-robin: priority/fill-first with capacity-aware pinned targets skips full targets, while round-robin rotates by policy even when the first target has capacity.

## Restart/port

A source checkout may have `.env` `PORT=20128` while the target listener is `20129` and 9Router owns `20128`. Before a restart, inspect the target PID command line and port resolver. Stop only the target process; relaunch with explicit `PORT`, `API_PORT`, `DASHBOARD_PORT`, and `OMNIROUTE_PORT`, plus the boot-time admission variables. Verify `/api/monitoring/health`, `/api/providers`, `/api/combos`, and listener ownership before testing. Do not report a WebSocket `server listening` watch-pattern event as an error; verify the process remains running and the API is healthy.
