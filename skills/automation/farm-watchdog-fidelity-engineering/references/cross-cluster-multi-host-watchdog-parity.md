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
| **Remote Git Parity & Dirty Working Tree** | Is the remote clone up-to-date with controller fixes? | Controller commits fixes locally, but remote clone remains at an older commit or has uncommitted modifications (`modified: file.py`), silently ignoring fixes ("Fixed N times already"). | Always verify commit SHA parity (`git rev-parse HEAD`) between hosts; clean/stash dirty remote working trees before running batches. |
| **Resource Assignment Manifest** | Does the remote cluster have its own valid assignment manifest? | Launchers requiring fail-closed resource ownership (`AssignmentManifest`) reject remote machines if manifest only contains local machines (M01-M80) or if manifest file is missing under remote `$LOCALAPPDATA`. | Deploy a cluster-specific manifest (`register-gmail-admin.json`) with resources for the remote machine partition (`machine:201`..`machine:280`) and matching `GMAIL_WORKER_ID` (`taadaa-writer-admin-farm`). |
| **Lock Root & User Profile Paths** | Does device locking resolve the remote user's directory? | Hardcoding controller's user path (`C:\Users\Kibe\.codex\device-locks`) causes permission errors or missing directories on remote node (`C:\Users\Admin`). | Use `$env:USERPROFILE\.codex\device-locks` or `$env:CODEX_DEVICE_LOCK_DIR` so lock paths dynamically resolve to the active host's user profile. |
| **Subprocess PYTHONPATH across SSH** | Can child processes import sibling packages? | Non-interactive SSH sessions do not inherit controller environment; child python scripts fail with `ModuleNotFoundError: No module named 'automation_core'`. | Launchers must self-bootstrap sibling paths (`$coreSrc = 'D:\Taadaa\automation-core\src'`) into `$env:PYTHONPATH` if absent. |
| **Telemetry Transport (Write-Host Trap)** | How does the remote script emit telemetry? | Launcher uses `Write-Host` to print `TOTAL=...`. In nested PowerShell subshells over SSH, `Write-Host` routes to Information Stream, NOT Stdout (Stream 1), so orchestrator regex parser receives empty string and defaults Admin to 0. | Always use `Write-Output` or direct stdout emission (`[Console]::Out.WriteLine(...)` or JSON stdout) for telemetry. |
| **Monolithic Aggregate Mask** | How does the alert display multi-cluster results? | Report lumps all stats under a single `[TOÀN FARM]` header without showing cluster-specific lines. When remote telemetry drops, report shows only local counts (e.g. 15 machines), misleading operator into thinking remote node never ran. | Multi-cluster reports MUST ALWAYS display split lines: `• Farm Kibe (M01-M80): ...` and `• Farm Admin (M201-M280): ...`. If a cluster returns 0, explicitly show `Hoàn tất 0 | Lỗi 0 (Chưa nhận telemetry / kiểm tra SSH)`. |
| **Coordinator Remote Probe Bridge** | How should Coordinator inspect remote node state? | Coordinator attempts raw `ssh admin-farm ...` in terminal, which is blocked by Coordinator guard `DEFAULT-DENY`. | Use canonical tool `python D:/Taadaa/tools/admin_ssh.py --powershell "<command>"` (allowlisted prefixes: `Get-`, `Set-`, `python`, etc.) or `--test` for sub-second, guard-compliant remote inspection. |

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
