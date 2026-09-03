# Runtime provenance and reboot proof

## Why a successful event can still hide a bad install

A watcher may show `WATCH_PROXY_APPLICATION_SUCCESS` and `WATCH_EVENT_VERIFIED_SUCCESS` while an independent probe of the configured Python reports an older `automation-core`. This can happen when `PYTHONPATH` or the wrapper environment redirects imports into a Hermes/global site-packages directory. Treat the event as proof of that particular process run only; it is not proof that the intended wheel is installed in the intended runtime.

## Mandatory provenance probe

For every executable that appears in the watcher process tree, run a fresh subprocess and record only sanitized metadata. Remove inherited `PYTHONPATH`, `PYTHONHOME`, and `VIRTUAL_ENV` for the probe; otherwise an interactive Hermes shell can shadow the selected interpreter and make both `importlib.metadata` and `automation_core.__file__` report the wrong installation:

```python
import inspect, sys
from importlib.metadata import version
from automation_core.device_recovery import watch_device_reconnect
import automation_core
print(sys.executable)
print(version("automation-core"))
print(automation_core.__file__)
print("auto_enable_wifi" in str(inspect.signature(watch_device_reconnect)))
```

The expected executable, package version, module path, and signature must agree. If `automation_core.__file__` points to an unrelated Hermes environment, inspect `sys.path`, `PYTHONPATH`, wrapper arguments, and the child process command before concluding the install succeeded.

## Safe correction sequence

1. Snapshot task XML, watcher process tree, repository diff, and the wheel hash/path.
2. Stop only the watcher component/tree before changing the package it imports; do not restart the Hermes gateway or unrelated schedulers.
3. Install the pinned wheel with `--force-reinstall --no-deps` into the exact runtime used by the task. Use a clean environment for the installer/probe so inherited `PYTHONPATH` cannot redirect imports.
4. Re-run provenance probes against every exact watcher executable. Do not proceed until the signature includes the feature the consumer passes and the module path is the intended installation.
5. Restart the dedicated tray/watcher, verify fresh PIDs and the exact mapping/runtime arguments, then inspect a new target-specific event log.
6. For a reboot test, correlate a fresh target boot ID with the new run. Require the event chain through `WATCH_EVENT_VERIFIED_SUCCESS`, then independently verify `adb get-state`, VPN interface `UP` plus `inet`, and Android VPN connectivity. Never expose serials, proxy values, or raw workbook rows.

## Common false conclusion

`requirements-automation-core.txt` pinning a wheel changes repository intent only; it does not install the wheel into a running venv. A successful `pip install` in one interpreter also does not prove the scheduled task's child interpreter uses that package. Installation, process provenance, event proof, and device proof are separate gates.
