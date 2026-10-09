# Omni-Worker Fallback Spillover — 2026-09-11

## Symptom
`omni-worker` (priority) spilled to `omni-free` (muse-spark/nemotron 502/504)
while `ag-gemini-pool-3` still showed many accounts with quota. Dashboard
`Requested Model combo/ag-claude 503` rows were canary probes, not worker traffic.

## Root causes found
- Tier order was Gemini → Free → Claude: any Gemini cap/exhaustion hit Free
  before Claude. Fix: Gemini → Claude → Free.
- `ag-claude` first ~30 targets were 21/30 exhausted (Claude bucket), so even
  correct tier order still fell through to Free.
- `omni-free` internal failover: muse-spark (#0, shared `noauth` connection)
  saturated under 8 parallel workers → fell to mimo → big-pickle → nemotron
  (#3), which 502/504-timed-out (135–160s). Provider breaker then skipped
  muse-spark on later requests, making nemotron appear "preferred".
- Session Stickiness (messageHash→connectionId, 15min TTL) pinned long worker
  sessions to one account and hit `maxConcurrent=2`.
- Prompt Cache Affinity (global scope, rendezvous hash) reordered cross-tier
  and could promote Free above Gemini/Claude.

## Fix applied
1. Reordered `ag-gemini-pool-3` + `ag-claude` physically GRP0–GRP4:
   GRP0 Pro quota>50% → GRP1 Starter ≥10% → GRP2 Starter low/exhausted →
   GRP3 standard-tier → GRP4 proxy dead/inactive.
2. `omni-worker`: Tier 1 Gemini → Tier 2 Claude → Tier 3 Free;
   `config.disableSessionStickiness=true`,
   `config.disablePromptCacheAffinity=true`, `maxGlobalAttempts=80`.
3. `omni-free`: removed `nemotron-3-ultra-free`, `nemotron-3.5-lightning-free`,
   then `muse-spark-1.2` (unstable Nvidia upstream).
4. Backup before PUT: `combos_backup_*.json`; PUT via
   `PUT /api/combos/{id}`; verify via SQLite `combos.data`.
5. Direct-egress account (`lelinh09111997`, no proxy row) bound to origin
   GPM proxy: profile `M09 - 5111` → `test.taadaa.click:5111`
   (`proxyId 93ffc9bf-...`) via `PUT /api/settings/proxies/assignments`
   `{"scope":"account","scopeId":cid,"proxyId":...}`.

## Verification queries
- Tier: `json.loads(combos.data).models[].comboName` for `omni-worker`.
- Pro count: `provider_specific_data.tier='g1-pro-tier'` (was 14, all in pool —
  do NOT conclude "missing accounts" without this query).
- Error accounts: `is_active=0 OR test_status!='active' OR last_error!=''`.
- Quota: latest `quota_snapshots` per `(connection_id, window_key)` for
  `gemini-3.8-flash-tiered` / `claude-sonnet-4-6`.
- GPM origin proxy: `Profiles.Name LIKE '%email%'` → `JsonData.Proxy`.

## Notes
- `reset-aware` already reorders per-request at runtime; physical reorder only
  sets a better starting point for LKGP/stickiness/affinity/pre-screen and
  debugging. Reorder on large changes (new accounts, mass exhaustion), not
  on every quota tick.
- 6 error accounts: 4 with GPM profiles dispatched for hot-session re-auth
  (keep 1:1 proxy, no device-activity/logout); 2 without profiles
  (`nguyenvysfj3102`, `vukhoa04122002`) need new profiles first.
