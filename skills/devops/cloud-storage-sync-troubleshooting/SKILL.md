---
name: cloud-storage-sync-troubleshooting
description: Troubleshoot and resolve sync errors, stuck files, authentication hangs, and notification issues for cloud storage clients (Google Drive, OneDrive, Dropbox, iCloud) on Windows.
category: devops
---

# Cloud Storage Sync Troubleshooting

## Overview
Systematic approach to diagnose and fix sync client issues on Windows: stuck "Lost and Found" notifications, orphaned files, database corruption, sign-in hangs, and sync loops.

## Trigger Conditions
- Persistent "Lost and Found" / "Bị thất lạc và đã tìm thấy" popup
- Files stuck in sync queue (0 bytes, never complete)
- Sync client high CPU / memory without progress
- Notification drawer shows unresolved sync errors
- iCloud desktop app stuck indefinitely on "Signing In..." with 0% CPU and CLOSE_WAIT sockets

## Google Drive for Desktop (Windows)

### Key Locations
| Purpose | Path |
|---------|------|
| App logs | `%LOCALAPPDATA%\Google\DriveFS\Logs\drive_fs.txt` |
| Lost & Found cache | `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\` |
| Metadata DB | `%LOCALAPPDATA%\Google\DriveFS\<account_id>\metadata_sqlite_db` |
| Mirror DB | `%LOCALAPPDATA%\Google\DriveFS\<account_id>\mirror_sqlite.db` |
| Root preferences | `%LOCALAPPDATA%\Google\DriveFS\root_preference_sqlite.db` |
| Executable | `C:\Program Files\Google\Drive File Stream\<version>\GoogleDriveFS.exe` |

### Diagnostic Steps
1. **Check Lost & Found cache**
   ```bash
   ls "%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\"
   ```
   - Files here = orphaned items Drive cannot sync
   - Empty folder = no stuck files

2. **Inspect recent logs**
   ```bash
   tail -50 "%LOCALAPPDATA%\Google\DriveFS\Logs\drive_fs.txt"
   ```
   - Search for: `lost_and_found`, `unsynced`, `notification`, `toast`, `error`, `warning`

3. **Query metadata DB for pending operations**
   ```python
   import sqlite3
   conn = sqlite3.connect(metadata_db_path)
   cur.execute("SELECT * FROM operations WHERE status != 'completed'")
   ```

4. **Check mirror DB for pending uploads/deletes**
   ```python
   conn = sqlite3.connect(mirror_db_path)
   for table in ["pending_uploads", "queued_uploads", "pending_deletes"]:
       cur.execute(f"SELECT * FROM {table}")
   ```

### Resolution: Stuck Lost & Found File
1. Identify the orphaned file name from cache or logs
2. Search all sync locations (G: drive, OneDrive, local Downloads, etc.)
3. **Verify the file exists correctly on cloud** (web UI or mounted drive)
4. Delete **all local copies** including:
   - Mounted drive path (G:\...)
   - OneDrive folder (if backup synced there)
   - Local Downloads / Documents
   - `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\`
5. Remove any backup folders created during prior recovery attempts
6. **Restart Google Drive FS**:
   ```bash
   taskkill /F /IM GoogleDriveFS.exe
   timeout /t 3
   start "" "C:\Program Files\Google\Drive File Stream\<version>\GoogleDriveFS.exe"
   ```
7. Verify: mount point (G:) remounts, logs show clean startup, no new notifications

### OneDrive (Similar Pattern)
- Lost & Found folder appears in OneDrive root
- Check `%LOCALAPPDATA%\Microsoft\OneDrive\logs\` for diagnostics
- Reset: `onedrive.exe /reset` then restart

### OneDrive Files On-Demand Dehydration Pitfall (0x401620 / Offline Recall)
- **Problem**: When files are created/modified on a remote node (e.g., Farm Admin PC) and synced to the local master (Farm Kibe) via OneDrive, Files On-Demand can leave the local file as a dehydrated cloud-only stub (attributes `0x401620`: `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS | FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_REPARSE_POINT`).
- **Symptom in Automation**: Python (`open()`, `openpyxl.load_workbook()`) and MSYS tools fail with `[Errno 22] Invalid argument`, `Permission denied`, or `zipfile.BadZipFile: File is not a zip file`. PowerShell throws `Exception calling "ReadAllBytes": The cloud file provider exited unexpectedly (0x8007017A)`.
- **Silent Batch Skip Pitfall**: If automation runners (e.g. `tiktok_runner.py`) catch generic `Exception` while reading the safe workbook, they treat the error as "0 valid accounts" and silently skip entire clusters (e.g. skipping 80 machines of Farm Admin).
- **Diagnosis via PowerShell**:
  ```powershell
  $item = Get-Item "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx"
  $isOffline = ([int]$item.Attributes -band 4096) -ne 0
  $isRecall = ([int]$item.Attributes -band 4194304) -ne 0
  Write-Host "Offline=$isOffline Recall=$isRecall"
  ```
- **Remediation (Pin / Always Keep on this Device)**:
  - Command Prompt / attrib:
    ```cmd
    attrib -u +p "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx"
    attrib -u +p /s /d "D:\OneDrive\TaadaaData\*.*"
    ```
  - Direct SCP fallback if OneDrive provider is wedged:
    ```bash
    scp admin-farm:D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx
    ```

### iCloud for Windows (AppX Sign-in Hang & AOSErrorDomain 1000)
- **Symptom**: App window frozen on "Signing In..." indefinitely (often showing an old account name like "Dat Bui"), CPU 0%, remote connection in `CLOSE_WAIT`.
- **Logs**: `%LOCALAPPDATA%\Packages\AppleInc.iCloud_nzyj5cx40ttqa\LocalCache\Local\Logs\iCloudHome.*.log` shows `Registration failed with error: (AOSErrorDomain error 1000.)` and `setting retry timer for 43200 second(s)...` (12-hour freeze timer).
- **Two-Layer Root Cause**:
  1. **Missing Root CA**: Microsoft Store AppX installation lacks `Apple Root CA` in Windows Certificate Store (`ROOT`), causing WinINet/Schannel to fail with `12045 (ERROR_INTERNET_INVALID_CA)` against `gsa.apple.com`.
  2. **Stale Session Token Deadlock**: Stale/expired session tokens in `%LOCALAPPDATA%\Packages\AppleInc.iCloud_nzyj5cx40ttqa\LocalCache\Roaming\Apple Computer\Preferences\com.apple.AOSKit.plist` and `Keychains\keychain-2.db` cause iCloud to attempt silent auto-resume of an expired session, failing with `kAOSErrorInvalidCredentials` and looping in the 12-hour retry instead of presenting the fresh sign-in UI.
- **Remediation**:
  1. Kill hung process tree: `taskkill /F /IM iCloudHome.exe /IM iCloudDrive.exe /IM APSDaemon.exe /IM iCloudCKKS.exe /IM secd.exe /IM iCloudOutlookConfig64.exe /IM ApplePhotoStreams.exe`
  2. Inject `Apple Server Authentication CA` into Windows `CA` store.
  3. Install official `AppleRootCA.cer` into `CurrentUser\Root` (via `certutil` or registry serialization).
  4. If frozen on an existing name: backup and remove `com.apple.AOSKit.plist`, `com.apple.AOSKit.RegInfo.plist`, `iCloudWinPref.plist`, and `keychain-2.db*` to force a clean login dialog.
  5. **Coordinator Anti-Lazy Mandate**: Do not offload manual `.bat` runs to the user; automate the execution and verification end-to-end.
  6. See detailed walkthrough in `references/icloud-windows-appx-signin-hang.md`.

## Pitfalls
- **Don't just dismiss notification** — file remains in cache, notification returns
- **Don't delete from cloud** — verify cloud copy is intact first
- **Killing process without cleanup** — orphaned DB locks may persist
- **Multiple sync clients** (Drive + OneDrive) can create duplicate copies in each other's folders
- **NTFS Junctions / Directory Symlinks do NOT sync content over OneDrive**: When sharing scripts or tool directories across machines via OneDrive (e.g. `mklink /J` or symlinks), OneDrive will not follow the junction or sync actual target files to other machines. Always sync real physical files (e.g., via a watchdog script copying `.py` files with `shutil.copy2`) into the cloud-synced directory structure.
- **Localized Root Folder Names in Google Drive FS**: Google Drive desktop virtual drive can use `G:\My Drive` (English) or `G:\Drive của tôi` (Vietnamese) depending on the account or OS language setting. Custom sync scripts must check `os.path.exists()` against both candidates dynamically rather than hardcoding one.
- **Transient / Hidden Files during File Sync**: Concurrent processes (Excel, sync engines) generate temporary dot-files or lock files (e.g., `.~...`, `.taikhoan_run_safe.*.xlsx`, `.849C...`). File sync workers must explicitly exclude files beginning with `.` or temporary prefixes to prevent `[Errno 2] No such file` (deleted while scanning) and `[Errno 13] Permission denied` (locked by OS).

## Verification Checklist
- [ ] Lost & Found cache empty
- [ ] No pending operations in metadata DB
- [ ] No pending uploads/deletes in mirror DB
- [ ] Drive mounts successfully (G: accessible)
- [ ] Log shows clean startup (no ERROR/WARNING in last 50 lines)
- [ ] No toast notification appears after 2-3 minutes

## References
- `references/google-drive-desktop-debugging.md` — Detailed log analysis, DB schemas, common error codes
- `references/onedrive-dehydration-automation-failures.md` — Root cause, error signatures (0x8007017A, Errno 22), and remediation for OneDrive dehydrated cloud files breaking automated batch loops
- `references/icloud-windows-appx-signin-hang.md` — In-depth breakdown of iCloud AppX sign-in freeze, WinINet error 12045, Apple PKI root CA import, and zombie process cleanup