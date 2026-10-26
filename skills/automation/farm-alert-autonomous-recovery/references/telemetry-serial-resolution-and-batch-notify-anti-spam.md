# Telemetry Serial Resolution and Batch Auto-Heal Anti-Spam Architecture

## 1. Context & Problem Statement
When background run-shift watchdogs (e.g. `feed_session_watchdog.py`) detect a script or device failure on a machine (e.g. `M48`), they emit an incident envelope via `incident_emitter.emit_if_needed(...)`. Two critical failure modes were identified:

1. **Serial Mapping Illusion (Blind Telemetry Bug):**
   - Watchdogs passed `serial=m_num` (e.g. `serial="48"` or `"16"`) into `emit_if_needed()`.
   - Raw ADB commands like `adb -s 48 exec-out screencap -p` and `adb -s 48 shell uiautomator dump` fail with `device '48' not found` because `48` is a farm slot number, not a hardware ADB serial.
   - Result: `screenshot` and `xml_dump` returned `None`, leaving the incident envelope empty of visual and structural evidence.
   - At Gate 0 (`run_gate_0_telemetry`), `IncidentAutoHarness` rejected the incident with `BLOCKED_PENDING_TELEMETRY` (completeness score < 2), preventing LLM repair from starting.

2. **Loop Notification Spam (Telegram Flooding):**
   - Inside `IncidentAutoHarness.run()`, every telemetry failure triggered `self.notify('BLOCKED_PENDING_TELEMETRY', 0)`.
   - When a batch of 18 machines failed in a shift, `process_queue()` emitted 18 individual Telegram alerts to `-5373649734` within seconds.
   - Result: Alert channel spam, forcing operators to manually `pause` the `incident-auto-heal-dispatcher` cron job.

---

## 2. Invariant Architecture: Dual-Cluster Serial Resolution
Never pass machine numbers directly to ADB. Before capturing telemetry:

1. **Local vs Remote Socket Partitioning:**
   - Machines `< 200` are Kibe Local: target default ADB daemon (`GEM_ADB` or `XIAOWEI_ADB`).
   - Machines `>= 200` are Admin Remote: target remote socket `-H 192.168.110.119 -P 5037`.
2. **Canonical Mapping via `inspect_machine.py`:**
   - Use `get_serial_for_machine(mid: int) -> tuple[str | None, str]` which parses `PROXYgandienthoai.xlsx` for the authoritative hardware serial.
   - In `incident_emitter.py`: If `serial` is numeric (`serial.isdigit()`), automatically resolve to the hardware serial and appropriate socket flags before issuing `screencap` or `uiautomator dump`.

```python
def resolve_serial_and_args(serial: str, machine_id: str = None) -> tuple[str, list[str]]:
    tool = ADB_BIN
    target = serial or machine_id or "1"
    try:
        from inspect_machine import get_serial_for_machine, ADB_BIN, ADMIN_IP, ADMIN_PORT
        m_str = str(machine_id if machine_id is not None else target)
        if m_str.isdigit():
            mid = int(m_str)
            s_val, _ = get_serial_for_machine(mid)
            if s_val:
                target = s_val
            if mid >= 200:
                return target, [ADB_BIN, "-H", ADMIN_IP, "-P", str(ADMIN_PORT), "-s", target]
    except Exception:
        pass
    return target, [tool, "-s", target]
```

---

## 3. Batch Notification Invariant (Silent Fail, Loud Success)
- **Individual Telegram notifications (`self.notify`) MUST ONLY be sent for `SUCCESS_MERGED`** (or when a critical single-ticket repair produces a valid media receipt and review score).
- **Batch failures / Blocked tickets MUST be consolidated**: `process_queue()` / `cron_incident_auto_heal.py` must emit at most ONE aggregated summary message at the end of the tick:
  ```text
  🤖 *[INCIDENT AUTO-HEAL DISPATCHER]*
  • Đã tự động vá & merge: N sự cố
  • Thất bại / Chuyển L3: M sự cố
  ```
- Any blocked ticket must be safely moved from `runtime/incidents/pending/` to `runtime/incidents/blocked/` to prevent infinite re-processing loops on future scheduler ticks.
