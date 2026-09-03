# Three-layer runtime verification (2026-08-28)

## Incident evidence

Hermes session `20260828_061203_8ede348c` used `ag-gemini-pool-3` through OmniRoute (`http://127.0.0.1:20129/v1`). At 06:12:08, the vision request failed with three `Proxy Fast-Fail` 502s against `test.taadaa.click:5111` and `:5104`; the diagnostics reported `poolSize: 3`, `attempted: 3`, and all three Antigravity connections exhausted. At 06:12:19, the retry returned HTTP 503 `ALL_TARGETS_SKIPPED` with `attempted: 0`, then the session switched to `gpt-5.6-luna`.

This is not proof of direct fallback failure by itself; it proves the request died in pre-dispatch filtering after the proxy candidates were exhausted. Because `attempted: 0` on the 503, `proxyFetch.ts` may never have been reached for that attempt, so `runDirect()` could not have executed.

## Correct verification checklist

1. Verify the intended order: account proxy -> provider fallback pool (including Mirotik) -> direct egress.
2. Correlate the same request ID/timestamp in Hermes `agent.log` and OmniRoute `server.log`.
3. Distinguish `Proxy Fast-Fail` / `ALL_TARGETS_SKIPPED` (pre-dispatch) from a `ProxyFetch` failure that explicitly enters `runDirect()`.
4. Inspect the serving process, not only the working tree or `.env`: confirm startup time, command line, deployed build/source, and effective `PROXY_FAIL_OPEN` / `OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK` values.
5. Require a fresh, minimal live request whose logs show the direct branch or a successful response after all proxy candidates fail. Do not infer Layer 3 from a closeout screenshot, a DB flag, or an unrelated `Proxy failed, falling back to direct` line.

## Safety

Do not disable accounts, delete/rebind pools, mutate model locks, restart services, or alter config during diagnosis unless explicitly authorized. A reported 3-layer setup and a live 3-layer execution are separate claims and must be reported separately.
