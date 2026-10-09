# Antigravity Pro VM Rescue & Guest Automation Pitfalls

## 1. VMware Guest File Copy & Attribute Lock Trap

### Symptom
`vmrun copyFileFromHostToGuest` or `vmrun deleteFileInGuest` fails with exit code `4294967295` (-1 / 127):
```text
Error: You do not have access rights to this file
```

### Root Cause
- Files provisioned into the guest baseline snapshot (e.g. `C:\ag-kit\` and subdirectories) often inherit `ReadOnly, Archive` file attributes from git or host copying.
- Windows API `CopyFile()` (with overwrite) and `DeleteFile()` explicitly return `ERROR_ACCESS_DENIED` on read-only files.
- `vmrun deleteFileInGuest` directly invokes `DeleteFile()`, failing on read-only targets instead of forcing removal.

### Proven Fix
Before calling `copyFileFromHostToGuest`, do not rely on `deleteFileInGuest` or in-place overwrite. Force removal and attribute clearance via guest PowerShell:
```python
vmrun_guest(
    "runProgramInGuest", VMX,
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "-ExecutionPolicy", "Bypass", "-Command",
    f"if (Test-Path -LiteralPath '{guest_path}') {{ Remove-Item -LiteralPath '{guest_path}' -Force }}",
)
r = vmrun_guest("copyFileFromHostToGuest", VMX, local_path, guest_path)
```

---

## 2. Antigravity Pro Scan & Classification Rules

Before investing VM boot or phone scan effort, run `scan_pro_accounts.py` to classify disabled accounts:
- **`BLOCKED` (403 `VALIDATION_REQUIRED`):** The only category requiring the VM rescue flow (real S7 proxy TUN + official Antigravity desktop app).
- **`QUOTA_EXHAUSTED` (429 `RESOURCE_EXHAUSTED`):** Account is healthy but out of quota on the shared family pool (`gemini-*` or `claude-*`). Do not rescue with VM; wait for quota reset.
- **`OK`:** Connection is healthy; enable directly via `enable.py <email>` or OmniRoute UI.
- **`INCONCLUSIVE` / `ERROR`:** Transient network/API issue; re-test before escalating.

---

## 3. Isolated Live Testing Invariant

- **Naive pinned chat tests give false positives:** OmniRoute may silently fall back or route requests to other active connections if the target fails or has session affinity.
- **Canonical isolation pattern:** `vm_rescue_lib.isolated_chat_test(conn_id)` temporarily disables all other active antigravity connections, enables and tests only the target connection, then restores previous state.

---

## 4. `vmrun` Pipe Hang Pitfall

- VMware helper processes spawned by `vmrun.exe` can hold stdout/stderr pipes open indefinitely, causing `subprocess.run(..., capture_output=True)` to block even beyond python timeouts.
- **Rule:** Always use `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` for `vmrun` automation and rely on exit code checks and guest log file polling.
