# VPN preflight pattern for reconcile scripts

## Required imports
```python
from automation_core.preflight import require_android_vpn, serial_is_mapped_in_workbook
```

`ConsumerPreflightError` lives in `automation_core.preflight` and is NOT
re-exported by consumer modules — always import it from the core module, never
from `tiktok_workflow.state_machine` or another consumer (that raises
`ImportError: cannot import name 'ConsumerPreflightError'` in tests).

## Worker-side fail-closed VPN gate (Phương án A, Tiktok-video 2026-08-15)

Upload consumers gate INSIDE the state machine so a live worker never touches
TikTok when VPN is down. Placement: the **first** thing in
`_handle_resolve_device` (RESOLVE_DEVICE), BEFORE serial/profile resolution —
never in `_handle_acquire_locks` when the repo has disabled device locks
(lockless consumers: the lock handler is a no-op, so the gate must live in a
handler that always runs for live runs).

```python
def _handle_resolve_device(self) -> bool:
    """RESOLVE_DEVICE: Resolve device info và profile."""
    logger.info("=== RESOLVE_DEVICE ===")
    device_id = self.context.config.get("device_id", "")

    # VPN gate (Phương án A): bắt buộc VPN CONNECTED trước khi resolve
    # serial/profile. Fail-closed — thiếu VPN => MANUAL_REVIEW.
    if not self.context.dry_run and device_id:
        adb_path = self.context.config.get("adb_path")
        adb_kwargs = {"serial": device_id}
        if adb_path:
            adb_kwargs["adb_path"] = str(adb_path)
        try:
            require_android_vpn(
                AdbClient(**adb_kwargs),
                required=True,
            )
        except Exception as e:
            raise WorkflowError(
                WorkflowState.RESOLVE_DEVICE,
                "VPN required before TikTok run",
                "VPN_REQUIRED_NOT_CONNECTED",
            ) from e

    row_serial = str((self.context.account_row or {}).get("device ID") or "").strip()
    ...
```

Contract rules:
- Skip gate when `dry_run` OR no `device_id` (guard sẵn có).
- `AdbClient(**{"serial": device_id, "adb_path": str(adb_path)})` — same kwargs
  shape the lock handler uses; only add `adb_path` when configured.
- Fail-closed on ANY exception from `require_android_vpn` (ConsumerPreflightError
  OR adb/timeout errors), wrapped `from e` so the cause chain is preserved.
- RESOLVE_DEVICE transitions to MANUAL_REVIEW, so the error surfaces as a
  reviewable state, never a silent skip.
- Regression tests monkeypatch `state_machine.require_android_vpn` /
  `state_machine.AdbClient` (module-level seam, NOT the core module directly).
  Three tests: VPN allowed → handler passes; ConsumerPreflightError →
  `WorkflowError` with tag `VPN_REQUIRED_NOT_CONNECTED`; dry_run → VPN never
  called. Full test code + verification recipe:
  `references/vpn-gate-resolve-device-20260815.md`.
- COMPAT entry pattern: `COMPAT-VPN-GATE-001` in `docs/tiktok-ui-compatibility.md`
  (signature = worker live on machine without VPN; fail-closed → MANUAL_REVIEW;
  regression test names). Registry files are CRLF — splice with
  `io.open(newline="")` + `\r\n` strings, then `file <path>` must still say CRLF.

## Pattern

Every reconcile entrypoint MUST:

1. **Accept `--proxy-mapping`** argument (default `None` — skips check when not provided).

2. **Before lock acquisition**: no action needed. VPN check runs AFTER lock.

3. **Inside `reconcile_target`**, after acquiring lock:
```python
if proxy_mapping is not None and proxy_mapping.is_file():
    adb = AdbClient(str(adb_path), target.serial, default_timeout=20)
    require_android_vpn(
        adb,
        required=serial_is_mapped_in_workbook(
            proxy_mapping, target.serial,
            serial_headers=("phoneId", "deviceId", "serial"),
        ),
    )
```

4. **In `acquire_device_lock`**, pass `live_vpn_verifier`:
```python
lease = acquire_device_lock(
    ...,
    live_vpn_verifier=lambda s: _check_tun0(adb_path, s),
)
```

5. **After reboot** (`_soft_reboot`), the `verify_post_reboot` callback must re-verify VPN:
```python
def _verify_vpn(adb, target, proxy_mapping):
    if not prepare_device(adb):
        return False
    if proxy_mapping is not None and proxy_mapping.is_file():
        require_android_vpn(
            adb,
            required=serial_is_mapped_in_workbook(
                proxy_mapping, target.serial,
                serial_headers=("phoneId", "deviceId", "serial"),
            ),
        )
    return True
```

## `_check_tun0` helper
```python
def _check_tun0(adb_path: Path, serial: str) -> bool:
    try:
        adb = AdbClient(str(adb_path), serial, default_timeout=10)
        result = adb.shell(["ip", "addr", "show", "tun0"], timeout=10)
        return result.ok and "inet " in str(result.stdout or "")
    except Exception:
        return False
```

## Router Proxy (wlan0) vs ViChanger (tun0) interface parameter trap

In `automation_core.preflight`, `require_android_vpn` historically defaulted to `interface="tun0"`.
When the farm runs in transparent **Router Proxy mode (`wlan0`)** without ViChanger (`tun0`), calling bare `require_android_vpn(adb, required=True)` causes `check_android_vpn` to treat `interface="tun0"` as an explicit override over `TAADAA_PROXY_MODE`, attempting ViChanger `GET_IP` on a non-existent `tun0` and raising `[VPN_REQUIRED_NOT_CONNECTED] ... tun0 tunnel is down or unassigned IP`.

**Rule:**
- When invoking `require_android_vpn`, always pass `interface="auto"` (or `"wlan0"` under router proxy mode) unless explicitly testing legacy ViChanger:
  ```python
  require_android_vpn(adb, required=True, interface="auto")
  ```
- In `automation_core.preflight`, `require_android_vpn` signature should default to `interface="auto"` so `TAADAA_PROXY_MODE` and dynamic Wi-Fi/wlan0 routing take effect cleanly across all consumers.

## Proxy readiness marker

`automation-core>=0.2.40` adds `wait_for_proxy_ready` inside `acquire_device_lock`. This reads from `~/.codex/device-readiness/<hash>.json`. The Gan proxy watcher writes `proxy_ready` state there. If the watcher hasn't written it yet, pass `live_vpn_verifier` to bypass the wait.
