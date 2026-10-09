# Remote ADB Client Routing & Fleet Architecture (automation-core)

## 1. Remote ADB Client Configuration (`automation_core.adb.AdbClient`)
When orchestrating Android farm devices spread across multiple host machines (e.g. Local Kibe daemon vs Remote Admin daemon at `192.168.110.119`):
- `AdbClient` accepts `host: str | None = None` and `port: int | None = None`.
- ADB arguments MUST position `-H <host>` and `-P <port>` **before** device-targeting `-s <serial>`:
  ```bash
  adb -H 192.168.110.119 -P 5037 -s <serial> <subcommand>
  ```
- Any sub-calls inside `AdbClient` that kick or wait for transport (`_reconnect_device()`, `_wait_for_device()`) must prepend `[-H self.host, -P self.port]` if `self.host` is configured. Omitting this routes reconnects to the local default daemon (localhost:5037), leaving remote hung connections unrecovered.

## 2. Fleet Machine Numbering Convention
In Taadaa farm orchestration:
- Machine index `N < 200`: Hosted locally on Kibe machine (`host=None`, localhost). Proxy/Serial map: `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`.
- Machine index `N >= 200`: Hosted remotely on Admin machine (`host="192.168.110.119"`). Proxy/Serial map: `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`.

## 3. Subprocess & Typing Pitfalls in automation-core
- When unpacking `**_subprocess_window_kwargs()` into `subprocess.run()`:
  Declare the return type as `dict[str, Any]` rather than `dict[str, int]`.
  In strict static type checkers (Pyright / mypy), unpacking `dict[str, int]` causes overload matching failures because other keyword arguments of `subprocess.run` (like `cwd`, `env`, `input`) do not accept `int`.
