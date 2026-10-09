# Remote ADB Centralized Multi-Host Farm Architecture (Kibe Master ↔ Admin Thin Worker)

## 1. Context & Problem (Dual-Master Syndrome)
Running independent Hermes Coordinator bots and separate Git repositories on both primary (Kibe: 1-80) and secondary (Admin: 201-280) PCs creates extreme maintenance friction:
- **Code Drift / Desync:** Bugfixes made on Admin are forgotten on Kibe (and vice versa). Operators waste mental bandwidth remembering which node has pulled latest fixes.
- **Fragmented Control Plane:** Having to chat with two distinct Telegram bots and manage two cron engines simultaneously.

## 2. Solution: Centralized Master Control Plane
Re-architect the farm to a **Single Control Plane (Kibe Master)** while keeping the secondary host (Admin) as a **Thin Worker Node (ADB Host Server + USB Controller)**:
```text
                 TAADAA CONTROL PLANE

                    KIBE PC
              Dual Xeon Master
        +---------------------------+
        | Hermes Core / Coordinator |
        | Cron Scheduler            |
        | Dual-Cluster Runner       |
        | GPM / OmniRoute Stack     |
        +---------------------------+
              /              \
     Local ADB              Remote ADB
    localhost:5037        Admin:5037
 (Machine 1-80)         (Machine 201-280)

                    ADMIN PC
        [Thin Worker / Standby Node]
          USB + ADB SERVER ONLY
        (Git retained for Disaster Recovery)
```

## 3. Key Invariants & Rules

### Rule 1: Cluster Isolation for Workbooks (Never Merge Safe Workbooks)
- **Do NOT merge workbooks into one massive file:** Merging 160+ machines creates severe `openpyxl` RAM and I/O lock contention, and enlarges the blast radius if an Excel corruption occurs.
- Keep per-cluster folders under OneDrive:
  - `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`
  - `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`
- Runner (`tiktok_runner.py`) spawns independent sub-sessions per cluster with isolated state files (`runner_simple_state.json`) and artifact trees.
- Always enforce the **3-Way Byte-Identical Invariant (SHA-256)** across:
  1. `%LOCALAPPDATA%\hermes\scripts\tiktok_runner.py`
  2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\tiktok_runner.py`
  3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\tiktok_runner.py`

### Rule 2: Remote ADB Routing in Automation-Core & Flow Runners
- `AdbClient` in `automation_core.adb` supports `host: str | None` and `port: int | None`.
  - Invariant: Always check `if self.port is not None:` (never `if self.port:`, to avoid dropping port 0).
  - Telemetry: Emits info log on remote initialization and warning log on remote reconnect.
- When machine ID $\ge 200$, `multi_machine_feed_session.py` (`_build_child_context`) and `inspect_machine.py` route commands through `-H 192.168.110.119 -P 5037`.
- When machine ID $< 200$, commands route through local ADB daemon.

### Rule 3: Gigabit Switch Bandwidth Realities
- 80 devices doing UI dumps, text taps, and screencap consume only ~3–5 MB/s peak network traffic.
- Over a 1Gbps Switch (<0.3ms latency), network overhead is <4% capacity. Hardware USB controller load remains on Admin's motherboard.

### Rule 4: OpenSSH Server for Out-of-Band Node Control
- Enable Windows OpenSSH Server on Admin (`D:\OneDrive\Taadaa_Sync_Shared\tools\setup_admin_ssh.ps1`).
- Key-based authentication via `~/.ssh/id_ed25519_kibe_admin` allowing Kibe to execute background OS maintenance, process checks, or cron adjustments on Admin via `ssh admin-farm "<command>"` without RDP/Ultraviewer.

### Rule 5: Disaster Recovery Standby
- Do NOT delete the Git repository or Python environments on Admin.
- Keep Admin as a cold standby node: if Kibe requires hardware maintenance, Admin's local cron can be unpaused immediately to resume standalone operation.

### Rule 6: Windows Kernel PortProxy Hardening for Remote ADB
- **The Problem:** Third-party tools like Xiaowei spawn ADB binding exclusively to loopback `127.0.0.1:5037`. Remote ADB commands from Kibe get `Connection refused` (10060/10061).
- **Hardened Solution:** Configure Windows Kernel PortProxy on Admin:
  ```cmd
  netsh interface portproxy add v4tov4 listenaddress=192.168.110.119 listenport=5037 connectaddress=127.0.0.1 connectport=5037
  netsh advfirewall firewall add rule name="ADB Remote 5037" dir=in action=allow protocol=TCP localport=5037
  ```
- **Durability:** Handled by IP Helper service (`iphlpsvc`, SYSTEM, AUTO_START), stored in Registry, completely immune to reboots or Xiaowei restart cycles. Zero downtime, zero ADB process-kill required.
- **Verification:**
  - `netsh interface portproxy show all`
  - From Kibe: `adb.exe -H 192.168.110.119 -P 5037 devices`
