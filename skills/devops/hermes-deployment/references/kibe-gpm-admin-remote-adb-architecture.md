# Kibe Single-Master & Admin Remote ADB over Gigabit LAN Architecture

## 1. Problem: Dual-Master Git Drift & Maintenance Overhead
In a two-host farm setup (Host A: Kibe [1-80], Host B: Admin [200-280]):
- Operating two active Hermes Coordinator bots and separate git workspaces creates **Dual-Master Drift**.
- Bug fixes committed on one machine require manual git pull, sync scripts, and verification prompts on the second machine.
- Operators suffer cognitive fatigue switching Telegram windows and tracking which machine has received code updates.

---

## 2. Technical Feasibility: Gigabit LAN Remote ADB

### Network Traffic Audit (80 Phones Concurrently)
A standard 1 Gbps switch provides ~110–125 MB/s bandwidth with < 0.3 ms intra-switch latency.
- **Control commands (`input tap`, `swipe`, `keyevent`)**: Tiny byte strings (< 10 KB/s across 80 devices).
- **UI hierarchy dump (XML via ATX/UIAutomator)**: ~150 KB per XML file. At 80 devices dumping every 5s: ~2.4 MB/s.
- **Screencaps / Evidence capture**: ~300 KB compressed PNG/JPEG. Event-driven: ~0.5–1.0 MB/s peak.
- **Total Peak Traffic**: ~3–5 MB/s (< 4% of Gigabit capacity).

### Hardware & Resource Allocation
- **Dual Xeon CPU Capacity**: Handling 160 ADB socket connections, OmniRoute/9Router proxy (< 1% CPU), and GPM (`MAX_WORKERS=2`, ~1.5 GB RAM) consumes only 10–20% of host CPU.
- **USB Controller Delegation**: The secondary PC (Admin) runs the ADB daemon (`adb -a -P 5037 nodaemon`), handling all physical USB hub interrupts. Kibe only dispatches network socket requests.

---

## 3. Remote ADB Setup & Verification

### On Secondary Node (Admin):
Listen for LAN connections on port 5037:
```cmd
adb kill-server
adb -a -P 5037 nodaemon
```
Ensure Windows Firewall permits incoming TCP connections on port 5037 from the local subnet (`192.168.110.0/24`).

### On Primary Node (Kibe):
Test connectivity:
```bash
adb -H 192.168.110.119 devices
```
Target a specific device:
```bash
adb -H 192.168.110.119 -s <serial> shell getprop ro.product.model
```

---

## 4. Device Mapping & Farm Integration
- **Workbook Mapping**: Admin device serials are cataloged in `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx` (Columns: `Máy`, `device ID`, `proXy`).
- **Inspection Routing**:
  - Machines `1 <= N <= 80`: local ADB (`adb -s <serial>`).
  - Machines `201 <= N <= 280`: remote ADB (`adb -H 192.168.110.119 -s <serial>`).
- **Result**: Operator interacts with 1 Hermes bot on Kibe, eliminating the secondary bot and zeroing out Git pull maintenance on Admin.

---

## 5. Architectural Invariants & Farm Scale Guardrails

### 1. Cluster Workbook Isolation (TUYỆT ĐỐI KHÔNG GỘP EXCEL)
- Keep Excel workbooks separated strictly by cluster:
  - Cluster 1: `D:/OneDrive/TaadaaData/kibe/` (Phones 1-80)
  - Cluster 2: `D:/OneDrive/TaadaaData/admin/` (Phones 201-280)
  - Cluster 3 (Future): `D:/OneDrive/TaadaaData/box_lan/` (Phones 301+)
- **Why**: Merging 160-500 phones (2,000-4,000 accounts) into a single Excel file causes massive openpyxl lock contention and risks farm-wide data corruption if a thread crashes during save. Central reporting is handled by reading cluster files and aggregating into one summary message on Telegram, never by merging raw sheets.

### 2. Cold Standby Node (Giữ Git trên Admin làm dự phòng thảm họa)
- Do NOT delete the Git repository or Python environment on Admin.
- Simply pause/remove the Telegram Bot and active Cron jobs on Admin to prevent concurrent runs.
- If Kibe suffers hardware failure or maintenance downtime, Admin can be restored to an independent standalone runner in minutes.

### 3. Future Scalability: Box Phone LAN Edge Gateway
- Mainboard box phones connected via LAN will connect directly to Admin or Kibe via IP (`adb connect <box_ip>:5555`).
- Admin functions as an Edge Gateway for hardware physically located near it, while Kibe remains the single dispatching brain.

### 4. ADB Socket & Network Defensive Measures
- **Concurrency Cap**: Use an `asyncio.Semaphore(25)` or thread pool limit (20-30 workers) for ADB subprocesses to prevent Windows `TIME_WAIT` socket exhaustion.
- **LAN Glitch Handling**: When LAN disconnects transiently, mark remote devices `DEGRADED` and retry with exponential backoff (1s, 5s, 15s, 60s). Never crash the primary scheduler.
- **Zombie Recovery**: Ping device with `adb shell echo ping` (5s timeout); if timed out, trigger `adb reconnect`.
