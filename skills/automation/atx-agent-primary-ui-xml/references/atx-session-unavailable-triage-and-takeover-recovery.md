# ATX Session Unavailable Recovery & Single-Machine Feed Canary

## Context & Symptoms
- Alert from Telegram / runner: `capture-invalid: ATX_SESSION_UNAVAILABLE`
- `summary.txt`: `stop_reason: capture-invalid: ATX_SESSION_UNAVAILABLE`
- Inspection with `ps -A` shows `atx-agent` process is alive, but `com.github.uiautomator` (stub) is missing from process list (`stub_process_lines: []`).

## Root Cause
- On low-end Samsung Galaxy devices (S7 / SM-G930*, Android 7/8), system memory pressure or app transitions can cause the UiAutomation background stub (`com.github.uiautomator`) to be terminated while `atx-agent` server remains running.
- ATX session requests fail to dump hierarchy because the underlying accessibility service is detached.

## Resolution Workflow

### 1. Hard Reset ATX Agent & Stub via Python Runtime
Execute via automation venv with cleared `PYTHONPATH`:
```python
from automation_core.adb import AdbClient
from automation_core.persistent_ui import capture_atx_session_ui, reset_atx_agent

client = AdbClient(adb_path=r"C:\Program Files (x86)\xiaowei\tools\adb.exe", serial="<SERIAL>", default_timeout=20)
# 1. Reset ATX Agent and restart stub via monkey
reset_atx_agent(client, timeout=20)

# 2. Verify capture returns VERIFIED_HEALTHY
cap = capture_atx_session_ui(client, timeout=20)
assert cap.health == "VERIFIED_HEALTHY"
assert cap.xml and "<hierarchy" in cap.xml
```

### 2. Verify Android VPN / Proxy Preflight
```python
from automation_core.preflight import check_android_vpn

vpn = check_android_vpn(client, required=True)
assert vpn.connected and vpn.tun_up, f"VPN not ready: {vpn.error}"
```

### 3. Single-Machine Canary / Takeover Run
When taking over a machine in `status: blocked` from an earlier failed run:
- **Option A (Multi-machine mode with Full Scope Takeover - Recommended)**:
```bash
env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe -u \
  "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
  --mode multi-machine-feed-session \
  --machines <MACHINE_ID> \
  --account-row-index <ROW> \
  --account-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
  --allow-navigation-only \
  --allow-feed-swipe \
  --allow-benign-popup-dismiss \
  --max-swipes 11 \
  --full-scope-takeover \
  --config "D:\Taadaa\tiktok-luot nuoi acc\python_runner\config.example.yaml"
```
*Note*: `multi-machine-feed-session` automatically handles device lock acquisition with `--full-scope-takeover`, executes feed swipes, verifies profile matching, performs home screen cleanup, and cleanly releases the lock upon completion.

- **Option B (Direct feed-session-smoke parameter syntax)**:
If invoking `feed-session-smoke` directly, note the exact flag names:
  - `--device <serial>` (NOT `--device-id`)
  - `--account <username>` (required)
  - `--account-row-index <row>` (NOT `--account-row`)
  - `--max-swipes <N>` (NOT `--recovery-test-swipes`)
  - Do NOT pass `--prepare-tiktok` or `--full-scope-takeover` (only valid in multi-machine mode).
