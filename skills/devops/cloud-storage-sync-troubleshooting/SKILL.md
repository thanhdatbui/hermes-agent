---
name: cloud-storage-sync-troubleshooting
description: Troubleshoot and resolve sync errors, stuck files, and notification issues for cloud storage clients (Google Drive, OneDrive, Dropbox) on Windows.
category: devops
---

# Cloud Storage Sync Troubleshooting

## Overview
Systematic approach to diagnose and fix sync client issues on Windows: stuck "Lost and Found" notifications, orphaned files, database corruption, and sync loops.

## Trigger Conditions
- Persistent "Lost and Found" / "Bị thất lạc và đã tìm thấy" popup
- Files stuck in sync queue (0 bytes, never complete)
- Sync client high CPU / memory without progress
- Notification drawer shows unresolved sync errors

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

## Pitfalls
- **Don't just dismiss notification** — file remains in cache, notification returns
- **Don't delete from cloud** — verify cloud copy is intact first
- **Killing process without cleanup** — orphaned DB locks may persist
- **Multiple sync clients** (Drive + OneDrive) can create duplicate copies in each other's folders

## Verification Checklist
- [ ] Lost & Found cache empty
- [ ] No pending operations in metadata DB
- [ ] No pending uploads/deletes in mirror DB
- [ ] Drive mounts successfully (G: accessible)
- [ ] Log shows clean startup (no ERROR/WARNING in last 50 lines)
- [ ] No toast notification appears after 2-3 minutes

## References
- `references/google-drive-desktop-debugging.md` — Detailed log analysis, DB schemas, common error codes