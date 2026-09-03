# OmniRoute three-layer proxy fallback: runtime verification

Session evidence (2026-08-28): Hermes called `ag-gemini-pool-3` through OmniRoute `http://127.0.0.1:20129/v1`. The live error was `Proxy Fast-Fail` on `test.taadaa.click:5111`, `:5104`, and `HTTP 503 ALL_TARGETS_SKIPPED`; no Mirotik or direct-fallback line appeared.

## Verify the actual DB and assignments

OmniRoute used `C:\Users\Kibe\.omniroute\storage.sqlite`, not 9Router's `AppData\Roaming\9router\db\data.sqlite`. The OmniRoute DB had 69 provider-scope assignments for `antigravity`: 35 Mirotik, 32 test.taadaa, and 2 KhoaLee, all `status=active`. However, the three affected Gemini connections had account-scope assignments to test.taadaa ports 5111, 5102, and 5104. The resolver in `src/lib/db/settings.ts` returns an account-scope proxy before checking provider scope, so provider-scope Mirotik is not automatically a second hop.

Useful read-only queries:

```sql
SELECT a.scope,a.scope_id,a.proxy_id,p.host,p.port,p.status
FROM proxy_assignments a LEFT JOIN proxy_registry p ON p.id=a.proxy_id
ORDER BY a.scope,a.scope_id;

SELECT p.host,p.status,COUNT(*)
FROM proxy_registry p GROUP BY p.host,p.status;
```

## Interpret the fallback layers

- Combo/model fallback is not proxy fallback.
- A log `poolSize: 3` refers to the three Gemini account targets, not 69 proxy candidates.
- `PROXY_FAIL_OPEN=true` in `open-sse/utils/proxyFetch.ts` can call `runDirect()` after `runWithProxyContext` observes an unreachable proxy. It does not make account resolution fall through to provider scope, and it cannot rescue a combo that returns `ALL_TARGETS_SKIPPED` before that helper is entered.
- `OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK` is documented for control-plane flows; do not claim it proves data-plane Gemini direct fallback.

## Runtime/version gate

Compare the running process creation time with the fix commit time and inspect startup logs. In this incident the dev process was created at `00:13:57`, while commit `35e288cb9` was created at `00:27:16`; the observed `06:12` failure therefore predates the running process loading that fix. Unit tests (`tests/unit/proxy-fetch.test.ts`) passed 9/9, but that only proves the isolated helper.

## Evidence required before claiming the chain works

Require a fresh canary showing at least one of:

1. actual dispatch through `mirotik1.taadaa.click:<port>`;
2. explicit `falling back to direct connection` runtime log;
3. fresh egress-IP evidence for the direct path.

Do not disable accounts, edit pool membership, reset OAuth, or call the chain fixed from screenshots, source code, `.env`, or unit tests alone. Restart is a separate operational action and requires approval; after restart, re-check process time and live logs.
