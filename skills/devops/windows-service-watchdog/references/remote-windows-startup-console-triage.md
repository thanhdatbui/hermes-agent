# Remote Windows Startup Console Triage

Use this when an interactive Windows farm host shows a Python/CMD window after reboot.

## Evidence-first sequence

Run bounded commands against the known host; do not scan the whole disk:

```bash
ssh <host> "powershell -NoProfile -Command \"Get-CimInstance Win32_Process | Where-Object { \$_.Name -match 'python|wscript|cscript|cmd|powershell' } | Select ProcessId,ParentProcessId,Name,CommandLine | Format-Table -Wrap\""
ssh <host> "powershell -NoProfile -Command \"Get-CimInstance Win32_StartupCommand | Select Name,Command,Location,User | Format-List\""
ssh <host> "powershell -NoProfile -Command \"Get-ChildItem '$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup' | Select Name,FullName\""
ssh <host> "powershell -NoProfile -Command \"Get-Process | Where-Object { \$_.MainWindowHandle -ne 0 } | Select Id,ProcessName,MainWindowHandle,MainWindowTitle,Path\""
```

Read the exact Startup `.vbs` and the watchdog it invokes. A VBS `WshShell.Run(..., 0, False)` wrapper can be correct while a nested Python `subprocess.run()` still creates a visible console.

## Interpret process evidence correctly

- A venv `python.exe` parent plus a base Python child with the same command line is often the normal Windows venv launcher chain, not two jobs.
- Follow `ParentProcessId` and command-line signatures before stopping anything.
- Keep active render/download/gateway workers running unless stopping them is explicitly requested; the visible console symptom is separate from worker liveness.

## Minimal patch contract

Patch only the exact nested console spawn:

```python
subprocess.run(
    [python_exe, launcher_p],
    check=True,
    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT,
)
```

Before editing, create a timestamped backup and require the old anchor to occur exactly once. Verify with:

```powershell
python -m py_compile C:\Users\Admin\watchdog_admin_render.py
Select-String -Path C:\Users\Admin\watchdog_admin_render.py -Pattern CREATE_NO_WINDOW
Get-Process | Where-Object { $_.ProcessName -eq 'python' } |
  Select Id,MainWindowHandle,MainWindowTitle,Path
```

Expected: syntax passes, the patched line is present, and relevant Python processes have `MainWindowHandle = 0`. If a remote `CopyFromScreen` attempt fails with an invalid handle, report that screenshot limitation separately; do not treat it as a regression of the headless patch.

## SSH quoting pitfall

The OpenSSH shell on a Windows target commonly routes through `cmd.exe`, while the controller shell expands `$` before PowerShell sees it. Escape PowerShell variables as `\$var`, or prefer a short remote PowerShell command with single-quoted literals. Avoid trying to transfer a multiline Python patch through deeply nested shell quoting; use a precise PowerShell string replacement or a base64 payload generated locally and decoded remotely.
