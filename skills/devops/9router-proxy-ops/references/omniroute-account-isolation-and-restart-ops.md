# OmniRoute Account Isolation and Safe Restart Protocol

Operational playbook for completely isolating Restricted/failing accounts from OmniRoute (`:20129`) SQLite storage, pruning combo definitions, and cleanly restarting the runtime under the Windows watchdog.

---

## 1. Complete Isolation: Two-Step Database Requirement

Disabling an account in `provider_connections` alone is **insufficient** if combos still have the connection hardcoded in their `data->models` array. OmniRoute combo runners can still attempt resolution or throw invalid model errors.

### Isolation Steps:
1. **Backup SQLite Database First:**
   Always copy `storage.sqlite` to `storage.sqlite.bak_<timestamp>` before making programmatic edits:
   `C:\Users\Kibe\.omniroute\storage.sqlite`
2. **Deactivate in `provider_connections`:**
   ```sql
   UPDATE provider_connections
   SET is_active = 0, updated_at = datetime('now')
   WHERE id IN (<restricted_ids>);
   ```
3. **Prune from `combos` Table:**
   - Combos store candidate models inside a JSON string in column `data`.
   - Iterate all rows in `combos`, parse `data`, and filter `data['models']`:
     Remove any model entry where `m.get('connectionId')` is in the restricted set, or where any restricted ID appears in the model definition.
   - Key combos to inspect: `ag-claude`, `ag-gemini-free-pool`, `ag-sonnet`, `omni-free`.
   - Update `combos` with serialized JSON and `updated_at = datetime('now')`.
4. **Mandatory DB Verification Queries:**
   - Confirm 0 restricted connections remain with `is_active = 1`.
   - Confirm 0 occurrences of restricted IDs in `data` across all rows in `combos`.

---

## 2. Python Script Template for Batch Account Isolation

```python
import sqlite3, json, shutil, os

DB_PATH = r"C:\Users\Kibe\.omniroute\storage.sqlite"
BACKUP_PATH = DB_PATH + ".bak_isolate"

RESTRICTED_IDS = [
    # list of target connection UUIDs
]
restricted_set = set(RESTRICTED_IDS)
shutil.copy2(DB_PATH, BACKUP_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Update provider_connections
placeholders = ','.join(['?'] * len(RESTRICTED_IDS))
cursor.execute(f"UPDATE provider_connections SET is_active = 0, updated_at = datetime('now') WHERE id IN ({placeholders})", RESTRICTED_IDS)

# 2. Prune models from combos
cursor.execute("SELECT id, name, data FROM combos")
for combo_id, combo_name, raw_data in cursor.fetchall():
    data = json.loads(raw_data)
    models = data.get("models", [])
    kept = [m for m in models if m.get("connectionId") not in restricted_set and not any(rid in json.dumps(m) for rid in restricted_set)]
    if len(kept) != len(models):
        data["models"] = kept
        cursor.execute("UPDATE combos SET data = ?, updated_at = datetime('now') WHERE id = ?", (json.dumps(data, ensure_ascii=False), combo_id))

conn.commit()

# 3. Verification
cursor.execute(f"SELECT COUNT(*) FROM provider_connections WHERE id IN ({placeholders}) AND is_active = 1", RESTRICTED_IDS)
active_remaining = cursor.fetchone()[0]
assert active_remaining == 0, f"Found {active_remaining} active restricted connections!"
conn.close()
```

---

## 3. Safe Runtime Restart via Watchdog

OmniRoute on Windows is supervised by `omniroute_watchdog.ps1` (`C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1`).
* **Watchdog behavior:** Polls `http://127.0.0.1:20129/api/health` every 15 seconds. If OmniRoute is down, it kills stale child processes and launches `scripts/dev/run-next.mjs`.
* **Dynamic PID Discovery:** NEVER rely on cached or static PIDs from previous turns. PIDs change upon each restart.
  - To locate the actual running Node.js process:
    ```bash
    netstat -ano | grep :20129
    ```
    or query the listening process via PowerShell:
    ```powershell
    (Get-NetTCPConnection -LocalPort 20129 -State Listen).OwningProcess
    ```
* **Restarting OmniRoute:**
  Kill the specific owning PID (e.g., `Stop-Process -Id <PID> -Force` or `taskkill /F /PID <PID>`).
  The watchdog will detect port unavailability on its next check cycle (within 15s) and launch a fresh Node.js instance loading the latest code and SQLite state.
* **Readiness Verification:**
  - Poll `http://127.0.0.1:20129/api/health` until HTTP 200 is returned.
  - Query new PID and StartTime:
    ```powershell
    Get-Process -Id (Get-NetTCPConnection -LocalPort 20129 -State Listen).OwningProcess | Select-Object Id, ProcessName, StartTime
    ```

---

## 4. Git-Bash / MSYS Shell Pitfall: PowerShell `$_` Expansion

When executing PowerShell snippets from Git Bash or MSYS bash:
* **The Hazard:** In double quotes (`"..."`), bash expands `$_` into the last argument or MSYS path (often `/c/Users/Kibe`).
* **Symptom:** PowerShell errors with:
  `/c/Users/Kibe.Name : The term '/c/Users/Kibe.Name' is not recognized as the name of a cmdlet...`
* **Safe Practices:**
  1. Use single quotes around PowerShell scriptblocks in bash:
     `powershell.exe -NoProfile -Command 'Get-Process | Where-Object { $_.ProcessName -eq "node" }'`
  2. Escape the dollar sign if double quotes are required: `\$_`
  3. Or write pure Python using `psutil` or `socket` to avoid shell escaping pitfalls altogether.
