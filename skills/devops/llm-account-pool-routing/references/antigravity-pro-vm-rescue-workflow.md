# Antigravity Pro Account Rescue Workflow & VMware Pitfalls

## 1. Context & Architecture
When Antigravity Pro accounts in OmniRoute get flagged by Google with `403 VALIDATION_REQUIRED` ("Verify your account to continue"), generic OAuth re-auth or bare browser sessions fail to clear the block. The proven rescue path uses a dedicated Windows VM (`D:\VM\ag-onboard\ag-onboard.vmx`), routes guest OS traffic via sing-box TUN to the account's real S7 phone proxy, and performs Google login inside the official Antigravity desktop app.

Scripts location: `D:\Taadaa\GPM auto\scripts\antigravity_rescue\`
Key scripts:
- `scan_pro_accounts.py`: Scans all disabled Pro accounts via `isolated_chat_test()` and classifies them (`BLOCKED`, `QUOTA_EXHAUSTED`, `OK`, `INCONCLUSIVE`).
- `rescue_antigravity_start.py <email>`: Automated setup (reverts VM to `baseline-v2.17`, starts VM, generates sing-box config, copies to guest, starts TUN, launches Antigravity app).
- `verify_and_finalize.py <email>`: Isolated live verification, activates provider in OmniRoute, and creates a verified VM snapshot.

---

## 2. VMware `vmrun` & Guest OS Pitfalls

### A. Overwriting ReadOnly Files in Guest
- **Symptom:** `copyFileFromHostToGuest` or `deleteFileInGuest` fails with exit code `4294967295` (-1). Output says `Error: You do not have access rights to this file`.
- **Root Cause:** Files in baseline snapshots or pre-copied kits often retain Windows file attributes `ReadOnly, Archive`. VMware's guest tools refuse in-place overwrite or guest-level deletion of read-only files.
- **Fix:** Use PowerShell inside the guest to clear attributes and force deletion before copying:
  ```python
  vmrun_guest(
      "runProgramInGuest", VMX,
      r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
      "-ExecutionPolicy", "Bypass", "-Command",
      f"if (Test-Path -LiteralPath '{guest_path}') {{ Remove-Item -LiteralPath '{guest_path}' -Force }}",
  )
  ```

### B. "The file is already in use" on `revertToSnapshot`
- **Symptom:** `vmrun revertToSnapshot` fails with exit code `4294967295`, `Error: The file is already in use`.
- **Root Cause:** The VM is currently running in the background (`vmrun list` shows it active, or `vmware-vmx.exe` holds file locks).
- **Fix:** Stop the running VM before reverting:
  ```bash
  vmrun -T ws stop "D:\VM\ag-onboard\ag-onboard.vmx" hard
  vmrun -T ws revertToSnapshot "D:\VM\ag-onboard\ag-onboard.vmx" baseline-v2.17
  ```

### C. Taking Screenshots of the VM for Verification
- **Command:** `vmrun -T ws -gu <user> -gp <pass> captureScreen <vmx_path> <host_png_path>`
- Note: The command is `captureScreen`, NOT `captureScreenInGuest`. It dumps a PNG screenshot of the VM's active display directly to a host path, which can then be inspected or delivered via `MEDIA:<path>`.

### D. GUI Interaction Boundary
- `runProgramInGuest` runs in a separate non-interactive guest session. Synthetic mouse/keyboard automation via `vmrun` does not reliably interact with the interactive desktop.
- Routine practice: Launch the app via `explorer.exe <shortcut>`, capture screen to verify readiness, and notify the user to click "Continue with Google" and complete login.
