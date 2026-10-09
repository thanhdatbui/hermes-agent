# Remote ADB Transport Reconnect & Inspection Recovery

## Context & Architecture
In dual-cluster Taadaa Farm operations:
- Kibe local devices (1-80) connect to host ADB (`localhost:5037`).
- Admin remote devices (201-280) connect via network ADB to Admin host (`192.168.110.119:5037`).

## Pitfall: Stale Transport / Socket Hanging on Individual Serial
When running `python D:/Taadaa/tools/inspect_machine.py <N>` on an Admin device (N >= 200), the command may fail with:
`Model: ERROR: Command '['...adb.exe', '-H', '192.168.110.119', '-P', '5037', '-s', '<serial>', 'shell', 'getprop', 'ro.product.model']' timed out after 10.0 seconds`

### Invariant: Do NOT Kill Remote ADB Server
Never run `adb kill-server` against `192.168.110.119:5037`. Doing so drops connections across all 80 active devices in the cluster, aborting concurrent sessions and batch runs.

### Canonical O(1) Recovery
Run targeted device reconnection:
```bash
adb -H 192.168.110.119 -P 5037 -s <serial> reconnect
```
Output:
`reconnecting <serial> [device]`

After reconnecting, immediately re-run:
```bash
python D:/Taadaa/tools/inspect_machine.py <N>
```
The device responds immediately without disturbing any other device in the fleet.
