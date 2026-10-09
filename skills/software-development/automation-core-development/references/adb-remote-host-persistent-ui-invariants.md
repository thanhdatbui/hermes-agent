# Remote ADB Host (ADB_SERVER_SOCKET / ADB_HOST) & Persistent UI Invariants

### 1. Root Cause & Architectural Invariant
When managing Android devices through an ADB cluster daemon or remote host (e.g., `192.168.110.119:5037` configured via `ADB_SERVER_SOCKET` or `ADB_HOST`):
- `adb.run(["forward", "tcp:0", "tcp:7912"])` or `adb.run(["forward", "tcp:7912", "tcp:7912"])` creates the listening socket on the **remote ADB daemon host**, NOT on the local machine loopback (`127.0.0.1`).
- Connecting to `http://127.0.0.1:{forwarded_port}` results in `ConnectionRefusedError (WinError 10061)` or timeouts, causing ATX persistent capture to fail closed (`ATX_SESSION_UNAVAILABLE`).
- The HTTP client targeting forwarded ports (atx-agent ping, jsonrpc `/session/<pid>:com.github.uiautomator/jsonrpc/0`, `/uiautomator`) MUST resolve the target host dynamically:
  1. `adb.host` if configured on the `AdbClient` instance.
  2. `os.environ.get("ADB_HOST")`.
  3. `os.environ.get("ADB_SERVER_SOCKET")` (parsing `tcp:<host>:<port>`).
  4. Fallback to `127.0.0.1` only when no remote host is configured.

### 2. AdbClient Remote Host Parsing Contract
`AdbClient.__init__` should automatically detect environment variables when `host` / `port` are not explicitly passed:
```python
if not self.host:
    env_host = os.environ.get("ADB_HOST")
    if env_host:
        self.host = env_host
    else:
        env_sock = os.environ.get("ADB_SERVER_SOCKET")
        if env_sock:
            cleaned = env_sock.removeprefix("tcp:")
            parts = cleaned.split(":")
            self.host = parts[0]
            if len(parts) > 1 and parts[1].isdigit() and self.port is None:
                self.port = int(parts[1])
```

### 3. Persistent UI Dynamic Host Binding
In `automation_core.persistent_ui`:
- Ensure `_request` accepts or dynamically resolves `target_host`.
- Keep positional argument signature compatible with test mocks: `_request(port, method, path, payload, timeout, host=None)`.
- Ensure `_ensure_forward` checks cached forward health via `f"http://{host}:{cached_port}/ping"`.
- Wrap capture lifecycles (`_session_dump_attempt`, `capture_persistent_ui`) with thread/context-safe host scoping so inner calls (`_ensure_forward`, `_request`) communicate with the remote ADB host socket.

### 4. Device Curl Transport & Telemetry Contract
When operating on remote hosts or as a fallback when HTTP transport fails:
- `_request_via_device_curl(adb, method, path, payload, timeout)`:
  - Executes `atx-agent curl` on device directly to bypass forwarding restrictions.
  - MUST verify `res.exit_code == 0` before parsing; non-zero exits or empty outputs must safely return `None`.
  - Safely catch `json.JSONDecodeError` and malformed output without raising unexpected unhandled exceptions.
  - **Module logger requirement**: `persistent_ui.py` must import `logging` and instantiate `logger = logging.getLogger(__name__)`. Using `logger.debug(...)` when `logger` is undefined causes `NameError`.
- Telemetry invariants in `_session_dump_attempt`:
  - `entry["elapsed_ms"]`: round execution time in milliseconds (`(time.monotonic() - started_at) * 1000, 3`).
  - `entry["transport_mode"]`: explicitly distinguish direct `"http"`, direct remote `"device_curl"`, or fallback `"http_fallback_to_device_curl"`.
  - When HTTP fails and falls back to curl, record `entry["fallback_trigger"] = type(http_exc).__name__`.

### 5. Verification Pitfalls with `test_persistent_ui.py`
- Running the entire `test_persistent_ui.py` suite may take ~6-10s; when testing specific changes, target individual tests:
  ```bash
  PYTHONPATH="D:\Taadaa\automation-core\src" python -m pytest tests/test_persistent_ui.py -k "test_resolve_host or test_is_remote_host" -v
  ```
