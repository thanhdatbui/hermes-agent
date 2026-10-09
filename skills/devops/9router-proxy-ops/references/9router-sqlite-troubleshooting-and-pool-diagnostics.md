# 9Router SQLite Troubleshooting & Pool Load Diagnostics

## 1. Locating the 9Router Database
- **Standard Windows Path:** `%APPDATA%\9router\db\data.sqlite` (`C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`).
- **Process detection:**
  - Avoid recursive full-drive searches (e.g. `glob.glob('C:/**/data.sqlite')` or root directory scans) on Windows/MSYS as they will hit timeouts (> 180s).
  - Use `netstat -ano | grep 20128` to find the 9Router PID, then inspect process open files via Python `psutil.Process(pid).open_files()`.

## 2. SQLite Schema Details
- **`providerConnections` table:**
  - Columns: `id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt`.
  - **Caution:** There is no `status` column. Account active state is tracked by `isActive` (1 = active, 0 = disabled).
- **`combos` table:**
  - Columns: `id, name, targets` (targets is a JSON string of targets and weights/priorities).

## 3. Investigating "Nominal vs. Real" Pool Mismatches
When users report a pool of nominal $N$ accounts (e.g., 80+ accounts) failing under load:
1. Verify how many accounts are actually imported into the 9Router database:
   ```sql
   SELECT count(*), provider, isActive FROM providerConnections GROUP BY provider, isActive;
   ```
2. Often, external scripts or pool configs reference a large inventory (e.g. 83 accounts), but 9Router's database only holds a small active subset (e.g. 7 Antigravity accounts).
3. Check if accounts are missing from 9Router completely or if they were never imported into `providerConnections`.

## 4. Why Traffic Bundles on Few Accounts (Ordered Spillover)
- 9Router's priority strategy is an **ordered waterfall / spillover** model based on the `priority` column (1 -> 2 -> ... -> N).
- Request dispatch always prioritizes the lowest numerical priority index (Priority 1) first.
- Only when Priority 1 is busy, rate-limited, or throwing 429/errors does traffic spill to Priority 2 and subsequent priorities.
- As soon as the rate-limit window or token bucket frees up on Priority 1, incoming requests immediately return to Priority 1.
- Consequence: Priority 1 to 3 accounts endure continuous hammering and quota exhaustion, while accounts further down the priority list receive little to no traffic until the top accounts are completely exhausted.
