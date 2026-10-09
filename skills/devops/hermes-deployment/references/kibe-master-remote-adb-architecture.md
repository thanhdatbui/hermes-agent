# Kibe Master & Remote ADB Fleet Architecture (Multi-Host Farm)

## 1. Context & Motivation
In a multi-host farm setup (e.g. Kibe PC + Admin PC each running 80 phones), running separate Hermes Coordinator bots and separate Git deployments on each host causes **Control Plane Fragmentation (Dual-Master Syndrome)**:
- Bug fixes applied on one host are forgotten or delayed on the other.
- Operator spends excessive cognitive effort syncing code, switching chat windows, and verifying git pull status.
- Dual Xeon host capacity is vastly underutilized (OmniRoute + GPM + ADB consumes < 5% CPU).

## 2. Master-ThinWorker Architectural Model
Instead of two independent peer coordinators:
- **Kibe PC = Master Controller (Single Control Plane)**:
  - Runs the sole Hermes Coordinator agent.
  - Houses the authoritative Git repositories, crons, and schedulers.
  - Manages all 160+ phones (local USB + remote LAN ADB).
- **Admin PC = Thin Worker / ADB Host Server (Standby Node)**:
  - Exposes ADB server over LAN: `adb -a -P 5037 nodaemon` (IP `192.168.110.119:5037`).
  - No active Hermes bot, no scheduler running during normal operation.
  - Retains Git repo locally in dormant mode solely for disaster recovery / cold-standby backup.

## 3. Data Isolation: Cluster Separation over Monolithic Merging
Do **NOT** merge multi-host Excel tracking sheets into a single giant workbook:
- **Excel I/O Bottleneck**: Large workbooks (thousands of rows across 160-500 devices) cause `openpyxl` file-locking contention, slow full-file serialization, and massive blast radius if corrupted.
- **Cluster Isolation**: Maintain separate directories:
  - `D:/OneDrive/TaadaaData/kibe/` (Cluster 1: Machines 1–80)
  - `D:/OneDrive/TaadaaData/admin/` (Cluster 2: Machines 201–280)
  - Future clusters (e.g. Box Phone LAN: Machines 301–400) receive their own directory.
- Reporting scripts aggregate results in memory in O(1) time without risking transactional workbook corruption.

## 4. Automation Core & ADB Client Abstraction
`automation_core.adb.AdbClient` natively routes commands based on host configuration:
- `host: str | None = None` and `port: int | None = None`.
- Commands prepended with `-H <host> -P <port>` before `-s <serial>`.
- `_reconnect_device` and `_wait_for_device` preserve remote host and port targeting.

## 5. Inspection Contract
`D:/Taadaa/tools/inspect_machine.py <N>` implements dual-cluster resolution:
- `N < 200`: Resolves serial via `TaadaaData/kibe/PROXYgandienthoai.xlsx` and calls local ADB.
- `N >= 200`: Resolves serial via `TaadaaData/admin/PROXYgandienthoai.xlsx` and calls `192.168.110.119:5037`.
- Returns standardized O(1) state: Model, Battery (% & status), Screen (ON/OFF), and foreground Focus Activity.
