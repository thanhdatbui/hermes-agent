# AdbClient Remote Host Routing and Port Invariants

## 1. Optional Integer Port Invariant (`port is not None`)
When handling network ports typed as `int | None`:
- **DO NOT** use `if self.port:` — in Python, `0` is falsy and will be dropped silently, breaking edge cases or test port fixtures.
- **DO** use `if self.port is not None:` in both argument builder (`_build_args`) and reconnect methods (`_reconnect_device`).

```python
# Good:
if self.host:
    command.extend(["-H", self.host])
if self.port is not None:
    command.extend(["-P", str(self.port)])

# Bad (drops port=0):
if self.port:
    command.extend(["-P", str(self.port)])
```

## 2. Remote ADB Telemetry & Logging
In multi-machine cluster/farm environments (e.g. Taadaa farm routing ADB commands to remote server instances), connection failures are common. AdbClient must provide structured observability:
- **Initialization Telemetry:**
  ```python
  if self.host:
      logger.info(f"AdbClient initialized with remote host={self.host}:{self.port or 5037} for serial={self.serial}")
  ```
- **Reconnect Telemetry:**
  ```python
  if self.host:
      logger.warning(f"Reconnecting remote ADB host {self.host}:{self.port or 5037} for serial={self.serial}")
  ```

## 3. Test Verification with `caplog` and Edge Cases
When writing or updating tests for `AdbClient` remote routing:
1. Verify `_build_args` includes `-H` and `-P` properly.
2. Explicitly test `port=0` to prevent regressions back to truthy checks:
   ```python
   client_port_zero = AdbClient(adb_path="adb.exe", host="10.0.0.1", port=0)
   assert client_port_zero._build_args(["devices"]) == ["adb.exe", "-H", "10.0.0.1", "-P", "0", "devices"]
   ```
3. Use pytest's `caplog` fixture to verify structured telemetry output:
   ```python
   with caplog.at_level(logging.INFO):
       AdbClient(adb_path="adb.exe", host="192.168.1.10", port=5037, serial="abc")
   assert "AdbClient initialized with remote host=192.168.1.10:5037" in caplog.text
   ```
