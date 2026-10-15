# Xiaowei ADB Port 5038 Rogue Conflict & Fail-Closed Process Cleanup Watchdog

## 1. Background & Root Cause (Xiaowei Dual-Port Architecture)
- **App Behavior:** Screen-mirroring tools like Xiaowei (玖卫 / xiaowei.exe, built with Rust Tauri) hardcode `tools/adb -P 5038 nodaemon server start` directly into their binaries (`src-tauri/src/adb/adb.rs`).
- **Dual-Socket UI:** The GUI connects to BOTH port 5037 and port 5038 simultaneously, aggregating all devices so the user sees a complete, seamless fleet.
- **Windows WinUSB Driver Isolation:** Windows WinUSB drivers do NOT permit two ADB server daemons to communicate with the same USB endpoint simultaneously. Whichever daemon binds a device first monopolizes its USB handle.
- **The Orphan Leak Trap:** When the user closes the Xiaowei window, the GUI process exits, but its background child daemon (`adb.exe -P 5038`) is abandoned as an orphan process.
- **Impact on Phone Farm Automation:**
  - Farm runners and scripts use the standard port `5037` (`localhost:5037` or remote `192.168.110.119:5037`).
  - Devices captured by port 5038 (e.g., 42/79 devices on Admin PC) vanish from port 5037 or timeout during socket initialization.
  - Schedulers and watchdogs misattribute these USB communication failures to *"App TikTok / Script crash"*, masking the true root cause.

---

## 2. Fail-Closed 3-State Logic (True / False / None)
When designing state-checking functions in watchdogs that perform destructive or cleanup actions (e.g., `kill-server`, `Terminate`), NEVER collapse query failures into `False`:

```python
from typing import Optional

def is_target_running() -> Optional[bool]:
    """
    Returns:
      True  -> Target process is confirmed running
      False -> Target process is confirmed NOT running
      None  -> Query failed, timed out, or permission denied (indeterminate)
    """
    try:
        r = subprocess.run(["tasklist", ...], capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            log_event("CHECK_ERROR", level="ERROR", returncode=r.returncode)
            return None  # Indeterminate error, NOT False!
        return "target.exe" in r.stdout.lower()
    except Exception as e:
        log_event("CHECK_ERROR", level="ERROR", error=str(e))
        return None  # Indeterminate exception, NOT False!
```

### Why collapsing `None` into `False` breaks farm safety:
1. **Pre-condition bypass:** If `is_gui_running()` returns `False` on a transient query error, the watchdog erroneously assumes the GUI is closed and triggers orphan cleanup while the user is actively using the app.
2. **False-positive success:** If `is_adb_running()` returns `False` on query error after a kill command, checking `if not is_adb_running()` evaluates to `True`, falsely logging `CLEANUP_OK` even when the rogue process was never terminated.

### Strict Fail-Closed Rules:
- **Pre-check:** `if is_gui_running() is not False or is_adb_running() is not True: return False`
- **Post-check:** `if r.returncode == 0 and is_adb_running() is False: return True`

---

## 3. Atomic In-Pipeline Race Prevention in Windows PowerShell / CIM
Sequential checks in Python (`check_gui()` then `kill_adb()`) suffer from Time-Of-Check to Time-Of-Use (TOCTOU) race conditions: if the user relaunches the GUI between the Python check and process termination, in-use ADB sessions get killed.

**Solution: Embed the parent check inside the PowerShell pipeline itself:**
```powershell
$targetPs = "$ports = Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess; Get-CimInstance Win32_Process -Filter \"Name = 'adb.exe'\" | Where-Object { $_.ProcessId -in $ports -and $_.ExecutablePath -like '*\xiaowei\*' }"

# Atomic pipeline: aborts termination immediately if xiaowei process appeared
$atomicCmd = "if (-not (Get-Process -Name xiaowei -ErrorAction SilentlyContinue)) { $targetPs | Invoke-CimMethod -MethodName Terminate }"
```

---

## 4. Avoiding `taskkill /T` on Shared Automation Hosts
- `taskkill /T` (Tree Kill) recursively terminates the target process and **all child processes**.
- In shared environments (where farm runners, adb wrappers, or helper tools may share job objects or environment trees), `/T` risks collateral damage against independent background daemons.
- **Rule:** Use `taskkill /F /IM target.exe` (without `/T`), and delegate orphan child cleanup to an explicit, strictly-filtered cleanup routine that verifies port ownership and executable path.

---

## 5. Reviewer & Closeout Gate Requirements
- **Diff Ceiling (<15KB):** Sol Reviewer truncates git diffs exceeding ~15KB (`TRUNCATION_MANIFEST`), resulting in severe score penalties. Use parameterized test suites (`@pytest.mark.parametrize`) to keep test files under 120 lines while maintaining 100% branch coverage.
- **Real Windows Integration Tests:** Sol Reviewer requires at least one test exercising real Windows API calls (`ctypes.windll.user32.GetLastInputInfo`, `tasklist`) alongside mocked unit tests to prove OS compatibility.
- **Long-Term Telemetry:** Ensure telemetry records (`log_event`) emit valid structured JSON with ISO timestamps and consistent event names (`*_OK`, `*_ERROR`, `*_ABORTED`).
