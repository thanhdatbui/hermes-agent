# Cross-Cluster Inventory Bleed and Missing Date-Directory Cluster Dropping

## 1. Problem Archetype
On multi-cluster device farms (e.g. Cluster Kibe M01-M80 vs Cluster Admin M201-M280):
1. **Rogue Inventory Injection:** A foreign machine ID (e.g., Machine 261 with serial `ce021602a92d1a0d04`) is accidentally pasted or merged into the local cluster's source tracking workbook (`taikhoan_dat_v2_updated .xlsx`).
2. **Propagated Host Guard Crash:** The synchronization cron (`taikhoan_sync_cron_launcher.py`) expands the rogue machine into the runtime safe workbook (`taikhoan_run_safe.xlsx`). When `tiktok_runner.py` dispatches `--machines 1..80,261`, the host safety guard (`taadaa_host.assert_machine_in_range(261, host)`) throws `HostConfigError: Machine 261 outside range [1, 80]`, terminating `run_tiktok.py` and the parent PowerShell launcher immediately at preflight.
3. **Missing Date Folder & Silent Watchdog Cluster Dropping:** Because the launcher crashed before creating `live/YYYY-MM-DD/row-X-...`, the cluster's daily directory never exists. The session watchdog (`feed_session_watchdog.py`) executes:
   ```python
   date_live = os.path.join(c_live, target_date)
   if not os.path.exists(date_live):
       continue  # <-- SILENT BLINDSPOT
   ```
   This `continue` completely bypasses the cluster reporting block, omitting the crashed cluster entirely from the user-facing alert (showing only Cluster Admin), leaving operators blind to the preflight outage.

---

## 2. Root Cause Analysis
- **Watchdog Flow Vulnerability:** The empty session reporter (`• Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)`) was guarded behind `if not session_runs:`. However, because `date_live` did not exist, the loop jumped straight to `continue` before checking `session_runs`, effectively dropping the cluster from `cluster_blocks`.
- **Preflight Host Guard Strictness:** `taadaa_host` is fail-closed (correct behavior to prevent cross-cluster execution). But upstream runners lacked range bounds validation, allowing a single malformed row to crash all 80 devices.

---

## 3. Engineering Invariants & Fix Contract

### Invariant A: Never Continue on Missing Date Directory
In session/batch watchdogs iterating over clusters:
```python
# BAD:
date_live = os.path.join(c_live, target_date)
if not os.path.exists(date_live):
    continue

# GOOD:
date_live = os.path.join(c_live, target_date)
runs = sorted(os.listdir(date_live)) if os.path.exists(date_live) else []
session_runs = []
# ... filter runs into session_runs ...
if not session_runs:
    block_lines = [
        f"🏢 【{cluster['label']}】",
        "• Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)",
    ]
    cluster_blocks.append("\n".join(block_lines))
    continue
```

### Invariant B: Inventory Fleet Range Pre-Filtering
Launchers and synchronizers must clamp machine candidates to the cluster's configured `machine_range`:
```python
fleet_min, fleet_max = cluster.get("fleet_min", 1), cluster.get("fleet_max", 80)
valid_machines = [m for m in candidate_machines if fleet_min <= int(m) <= fleet_max]
```

### Invariant C: Remediation Tooling for Rogue Workbook Rows
Maintain deterministic cleanup scripts to audit and prune out-of-range machine rows from both the raw tracking workbook and the safe runtime workbook.
