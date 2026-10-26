# Cross-Cluster Multi-Host Watchdog & Telemetry Parity

## 1. Problem Statement & Anti-Pattern
In distributed farm architectures consisting of a primary orchestrator node (e.g. Kibe, controlling local devices M01-M80) and a remote worker node (e.g. Admin, controlling M201-M280 reachable via SSH), multi-stage batch watchdogs frequently suffer from **Silent Remote Fleet Dropping**.

When the watchdog runs:
1. Local cluster completes execution and produces structured telemetry (e.g., in `D:/CodexRuntime/.../summary.json`).
2. Remote cluster either:
   - Fails to start due to path mismatch in SSH invocation (e.g., local repo path `D:/Taadaa/register gmail` vs remote repo structure).
   - Resolves an empty device inventory because the local inventory workbook (`taikhoan_run_safe.xlsx`) lacks entries for the remote machine range (`201-280`).
   - Runs remotely, but the orchestrator only reads the local machine's runtime summary directory, silently treating the remote cluster as 0 machines.
3. The watchdog aggregates `total = kibe.total + admin.total` where `admin` is `0`, leading the operator to complain: *"Fixed this N times, why does it still stubbornly refuse to run on Admin farm?"*

---

## 2. Root Cause Checklist for Remote Cluster Dropping

| Layer | Check | Common Pitfall | Remediated Contract |
|---|---|---|---|
| **Inventory Source** | Does the runner load both local and remote device maps? | `taikhoan_run_safe.xlsx` only contains M01-M80; Admin M201-M280 is in `TaadaaData/admin/PROXYgandienthoai.xlsx`. | Runner must union both maps or explicitly pass `--device-map` matching the target cluster. |
| **Execution Environment** | Are remote paths valid on the remote host? | Script passes Kibe's local Python exe (`C:/Users/Kibe/...` or `PYTHON_EXE`) which does not exist under user `Admin`. | Use host configuration (`admin.yaml`) or `ADMIN_PYTHON` (`D:/Taadaa/python-envs/automation/...`). Never leak orchestrator's local user path via `$env:GMAIL_REG_PYTHON_EXE`. |
| **Windows Path Syntax in SSH PS** | Are path separators compatible with Windows PowerShell over SSH? | Passing forward slashes (`Set-Location 'D:/Taadaa/register gmail'`) over SSH causes PowerShell `Test-Path` to return False (exit 1). | Use native Windows backslashes (`D:\Taadaa\register gmail` via `os.path.normpath` or `str(path).replace('/', '\\')`). |
| **Telemetry Transport** | How does the orchestrator collect remote results? | Orchestrator looks only at local disk (`glob("D:/CodexRuntime/.../summary.json")`). Remote results stay on the remote disk. | Remote invocation must output structured JSON to stdout wrapped in a delimiter (e.g. `=== SUMMARY JSON ===`), or orchestrator must retrieve remote artifacts. |
| **Telemetry Aggregation** | Does the report surface missing clusters? | If `admin.total == 0`, report silently shows local results without warning. | If target cluster is expected to participate, `admin.total == 0` must trigger a visible alert: `⚠️ Cluster Admin: 0 máy được thực thi / telemetry thất lạc`. |

---

## 3. Reference Implementation Pattern

```python
def run_cluster_batch(cluster_name: str, host_config: dict) -> tuple[int, dict]:
    """Execute batch on cluster and return exit code + structured summary dict."""
    if host_config.get("is_local"):
        return _run_local_batch(host_config)
    
    # Remote SSH execution with explicit host parameters
    ssh_host = host_config["ssh_host"]
    remote_python = host_config["python_exe"]
    remote_repo = host_config["repo_dir"]
    remote_inventory = host_config["inventory_workbook"]
    
    ps_cmd = (
        f"$env:PROXY_DIENTHOAI_PATH='{remote_inventory}'; "
        f"Set-Location '{remote_repo}'; "
        f"& '{remote_python}' -m runner.cli --json-stdout; "
        "exit $LASTEXITCODE"
    )
    code, stdout = run_ssh_ps(ssh_host, ps_cmd)
    summary = parse_stdout_json(stdout)
    
    if not summary and code != 0:
        summary = {"total": 0, "success": 0, "failed": 0, "error": f"SSH/Runner failure (code={code})"}
    elif not summary:
        summary = {"total": 0, "success": 0, "failed": 0, "warning": "No telemetry returned from remote cluster"}
        
    return code, summary
```
