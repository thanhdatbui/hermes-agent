# Runtime reconciliation and focused verification

Use this when a Windows consumer is pinned to a newer `automation-core` wheel but the live watcher imports an older copy.

## Root-cause probe

1. Inspect the exact scheduled-task XML, wrapper arguments, process tree, and each exact Python executable.
2. For each executable, run the import probe with inherited `PYTHONPATH` visible and then with it cleared:

```python
import inspect, importlib.metadata as metadata
import automation_core
from automation_core.device_recovery import watch_device_reconnect
print(metadata.version("automation-core"))
print(automation_core.__file__)
print(inspect.signature(watch_device_reconnect))
```

The decisive evidence is the combination of distribution version, module path, and signature. A requirements pin alone is not runtime proof.

## Safe Windows fix

- Record task/process state and preserve dirty repo state.
- Stop only the named watcher component; do not stop unrelated schedulers or gateway processes.
- Install the wheel with the exact runtime executable and `--force-reinstall --no-deps`, using a Windows path (`D:/...`), not an MSYS `/d/...` path.
- If the wrapper inherits a global Hermes `PYTHONPATH`, clear it before assigning the consumer scripts path:

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:PYTHONPATH = Join-Path $ganProxyRoot 'scripts'
```

- Restart only the scheduled watcher and verify singleton count, command line, task state, clean stderr, and the same import/signature probes after restart.

## Live-device gate

For a single authorized machine: load the existing mapping without printing serial/proxy, inspect both central lock aliases, and never take over an active live owner. If a stale probe owner is demonstrably dead, use the shared core's authorized takeover/release path rather than deleting lock files manually. Perform at most one soft reboot through the existing core path, then require event evidence (`DETECTED`, `CORE_READINESS_PASS`, `PROXY_APPLICATION_SUCCESS`, `VERIFICATION_SUCCESS`, `READINESS_READY`, `VERIFIED_SUCCESS`) plus live ADB state, `tun0` UP+inet, and VPN connectivity.

## Focused ad-hoc verification

When the environment reports a changed file as unverified and no canonical checker is detected, create a temporary script via `tempfile.NamedTemporaryFile(prefix="hermes-verify-", dir=<Windows Temp>, delete=False)`. Assert the changed wrapper contains exactly one clear-before-assign sequence, run a minimal PowerShell environment probe, execute the script, and remove it in a `finally`/cleanup step. Report this explicitly as **ad-hoc verification**, not as a green suite.

Do not print secrets, serials, proxy values, or full credential-bearing environments in evidence artifacts.
