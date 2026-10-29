# Bulkhead Device Isolation & Host Range Safety Invariant

## Context & Problem
On Taadaa Farm, the fleet is split across multiple host machines (e.g. Host `kibe` running machines 1-80, Host `admin` running machines 201-280).
A rogue row, typo, or sync error in workbooks (e.g. `taikhoan_dat_v2_updated .xlsx` containing Machine 261 under Kibe) can introduce an out-of-range machine ID into the candidate list.

## Anti-Pattern (Blanket Abort / Fail-Closed Crash Trap)
```python
# BAD: Crashing the entire batch run if even 1 machine is out of range
if args.machines:
    for _part in str(args.machines).split(","):
        _m = _part.strip()
        if _m.isdigit():
            taadaa_host.assert_machine_in_range(int(_m), _host) # Throws HostConfigError!
```
When this fires, the entire multi-machine feed/follow/upload session crashes during preflight before spawning a single device. All 80 healthy devices are prevented from running.

## Invariant Rule (Bulkhead Isolation)
Never fail-closed on the entire fleet due to out-of-range or offline machine IDs.
Filter out the invalid machines, log a clear warning, and continue executing the valid subset:

```python
# GOOD: Filter out invalid machines, keep valid machines running
if args.machines:
    valid_machines = []
    for _part in str(args.machines).split(","):
        _m = _part.strip()
        if _m.isdigit():
            m_int = int(_m)
            try:
                taadaa_host.assert_machine_in_range(m_int, _host)
                valid_machines.append(str(m_int))
            except taadaa_host.HostConfigError as _herr:
                print(f"[HOST_WARNING] Bỏ qua machine {m_int} không thuộc host: {_herr}", file=sys.stderr)
    if not valid_machines:
        print("CONFIG_ERROR: Không còn machine nào thuộc host hợp lệ sau khi lọc", file=sys.stderr)
        return ExitStatus.CONFIG_ERROR.code
    args.machines = ",".join(valid_machines)
```
