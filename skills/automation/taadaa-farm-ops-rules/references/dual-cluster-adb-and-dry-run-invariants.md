# Dual-Cluster ADB Routing, Dry-Run, and Closeout Invariants

## 1. Dual-Cluster Topology
* **Cluster Kibe (Local)**: Machines 1–80, workbook `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx`, direct USB connection via local ADB.
* **Cluster Admin (Remote)**: Machines 201–280, workbook `D:\OneDrive\TaadaaData\admin\Tik1.xlsx`, USB connection to Admin PC, reached via LAN socket `tcp:192.168.110.119:5037` (`-H 192.168.110.119 -P 5037`).

## 2. ADB Environment & Leaking Socket Prevention
When building or upgrading dual-cluster scripts:
* **Admin execution**:
  ```python
  if cluster.get("adb_socket"):
      env["ADB_SERVER_SOCKET"] = cluster["adb_socket"]
  ```
  And teardown/adb CLI commands must prepend `cluster["adb_args"]` (e.g. `[ADB, *cluster["adb_args"], "-s", serial, "shell", ...]`).
* **Kibe execution (Crucial)**:
  ```python
  else:
      env.pop("ADB_SERVER_SOCKET", None)
  ```
  Failure to `pop()` causes environment leaks: if a prior process exported `ADB_SERVER_SOCKET`, local Kibe commands will attempt to connect to the remote socket and fail or misroute.

## 3. Dry-Run & Retry Counter Invariants
* **Dry-Run Purity**: When `--dry-run` is requested:
  ```python
  if args.dry_run:
      sys.stderr.write(f"[CRON][DRY-RUN] Would clear {len(target_machines)} machines; state unchanged.\n")
      return 0
  ```
  `--dry-run` must NEVER mutate `machine_retries`, update `cleared_machines`, or call `save_state()`.
* **Failure-Only Retry Increment**:
  Do NOT increment retry counters before task execution. Increment ONLY inside the failure branch (`else:` where `msg` does not contain `[LOCKED]`):
  ```python
  machine_retries[str(m_num)] = machine_retries.get(str(m_num), 0) + 1
  state_data["machine_retries"] = machine_retries
  save_state(state_data)
  ```
  Pre-incrementing exhausts the device's daily retry budget prematurely if the process crashes or times out before running.

## 4. Telemetry & Cluster Reporting
* Always prefix operational logs with cluster identity: `sys.stderr.write(f"[{c_name.upper()}] {msg}\n")`.
* Report results grouped by cluster:
  - `🏢 【FARM KIBE - MÁY 1-80】`
  - `🏢 【FARM ADMIN - MÁY 201-280】`
* Record cluster breakdown metrics in state JSON (`last_cluster_stats`).

## 5. Closeout Gate Audit Binding
* `closeout_gate.py --repo <path> --base HEAD~1` extracts diff against `HEAD~1` and binds against `HEAD`.
* To review scoped changes without exposing foreign dirty files, stage and commit the owned changes to local `HEAD` before invoking `closeout_gate.py`.
* CẤM push lên remote trước khi reviewer trả về `Verdict: APPROVED (Score >= 85)`.
