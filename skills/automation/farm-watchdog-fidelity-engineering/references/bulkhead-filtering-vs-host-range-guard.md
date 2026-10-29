# Bulkhead Isolation vs Host Range Guard Case Study

## 1. Problem Description
On a distributed device farm (e.g. Host Kibe managing machines 1-80, Host Admin managing machines 201-280), workbook sync or manual edits occasionally introduce cross-host / rogue entries (e.g. M261 appended into Kibe's workbook).

### The Anti-Pattern: Blanket Batch Abort
A preflight or CLI entrypoint parses `--machines 1,2,...,80,261`.
The host guard executes:
```python
if args.machines:
    for _part in str(args.machines).split(","):
        _m = _part.strip()
        if _m.isdigit():
            taadaa_host.assert_machine_in_range(int(_m), _host)
```
When `assert_machine_in_range(261)` raises `HostConfigError`, the script immediately exits with `CONFIG_ERROR` before launching any device automation. Consequently, **all 80 healthy local devices are aborted** simply because 1 rogue machine ID was in the candidate list.

## 2. Invariant & Contract: Individual Bulkhead Filtering
When `--machines` is supplied with candidate devices:
1. Validate each candidate individually.
2. If a machine fails `assert_machine_in_range`, log a structured warning and drop it from the target list.
3. Fail closed (`CONFIG_ERROR`) **only if 0 valid machines remain** for this host after filtering.
4. Re-assign `args.machines = ",".join(valid_machines)` and allow the remaining valid fleet to execute unimpeded.

```python
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
