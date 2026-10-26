# Account Lifecycle vs Router Pool Reconciliation

When operators ask why an upstream-registered account pool (e.g. ChatGPT Web, Codex, Claude, social accounts) has fewer active connections in a local LLM proxy/router (e.g. OmniRoute, 9Router) than expected ("I remember registering hundreds of accounts, why does the pool have so few?"):

## 1. Disconnect Taxonomy: Upstream Stock vs Downstream Active Pool

Never conclude accounts were banned or lost based solely on the router's active connection count. Distinguish the 4 operational inventory layers:

1. **Raw Registered Inventory (Upstream Lifecycle DB)**:
   - Accounts registered and stored in automation supervisor state files (e.g. `batch_gpm_5profiles_supervisor_state.json`).
   - Indicator: `has_chatgpt: true` or valid credentials present.
2. **Soaking / Safety Maturation Queue**:
   - Accounts undergoing anti-mass-ban quarantine (e.g. `WAIT_7D`, 48h proxy cool-off, or `CHANGE_INFO`).
   - These accounts are deliberately held back from production API traffic to prevent sentinel triggers.
3. **Matured / Ingestion-Ready Fleet**:
   - Accounts that have reached terminal safe lifecycle stages (e.g. `stage: "DONE"`).
   - Ready for injection into downstream routers, but waiting for feeder dispatch.
4. **Active Gateway Pool (Downstream Router DB)**:
   - Accounts imported into `storage.sqlite` / `provider_connections` with `is_active = 1`.
   - Constrained by provider quotas, concurrency caps, proxy assignment hygiene, and feeder pacing limits.

## 2. Diagnostic & Triage Protocol O(1)

When reconciling account count discrepancies:

1. **Step 1: Inspect Live Router State**:
   Query router DB (`storage.sqlite`) directly:
   ```sql
   SELECT provider, is_active, count(*)
   FROM provider_connections
   GROUP BY provider, is_active;
   ```
   Determine if accounts are missing from the table or merely marked `is_active = 0` (isolated / soaked).

2. **Step 2: Inspect Farm Lifecycle State**:
   Read state files at known paths (e.g. `D:/Taadaa/runtime/<cluster>/cron-state/batch_gpm_5profiles_supervisor_state.json`) without scanning the disk recursively.
   Group by `stage` and verify `has_chatgpt` counts across clusters (e.g. Kibe vs Admin).

3. **Step 3: Check Feeder Job State**:
   List scheduled cronjobs (`cronjob(action='list')`) and check the status of feeder runners (e.g. `cron-auto-feed-chatgpt-pool`, `omni-activate-soaked-codex`).
   A paused feeder or rate-limited feeder batch (e.g. 5 accounts per cycle) naturally caps the active pool size while hundreds of matured accounts wait in upstream storage.
