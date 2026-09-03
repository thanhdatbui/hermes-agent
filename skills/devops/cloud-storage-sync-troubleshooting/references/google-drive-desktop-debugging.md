# Google Drive for Desktop Debugging Reference

## Session: 2026-09-02 - Lost & Found Stuck File

### Problem
- Persistent "Bị thất lạc và đã tìm thấy" (Lost and Found) notification in system tray
- File: `GemPhoneFarm Setup.exe` (224 MB)
- Account: `jinrakal@gmail.com` (account_id: `101571154735878537337`)

### Root Cause
File was partially synced / conflicted during upload. Google Drive moved it to local `lost_and_found` cache but could not resolve. Notification fires repeatedly until cache is cleared.

### Key Log Entries (drive_fs.txt)
```
notification_severity: NOTIFICATION_SEVERITY_INFO
notification_priority: NOTIFICATION_PRIORITY_LOW
NotificationCard = id: 8
Display Notification: "Có tệp chưa đồng bộ hoặc không bị bỏ lỡ vì đã được di dời..."
```

### Database Inspection
**metadata_sqlite_db** (local metadata):
- `items`: 34,680 rows
- `operations`: 3,869 rows
- `stable_parents`: 34,676 rows
- `local_stable_ids`: 953 rows (local-only items)

**mirror_sqlite.db** (cloud mirror):
- `mirror_item`: main item table
- `pending_uploads`: 0 rows
- `queued_uploads`: 0 rows
- `pending_deletes`: 0 rows

**root_preference_sqlite.db**:
- `notifications`: 0 rows (after cleanup)
- `roots`: 0 rows
- `media`: 35 entries (includes Google Drive G:, OneDrive, USB devices)

### File Locations Found
| Location | Status |
|----------|--------|
| `G:\Drive của tôi\Backup_OneDrive_5TB\Documents\Downloads\GemPhoneFarm Setup.exe` | Cloud copy (intact) |
| `D:\OneDrive\Documents\Downloads\GemPhoneFarm Setup.exe` | OneDrive backup copy |
| `C:\Users\Kibe\OneDrive\Documents\Downloads\GemPhoneFarm Setup.exe` | OneDrive local copy |
| `C:\Users\Kibe\Downloads\GemPhoneFarm Setup.exe` | Local download |
| `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\101571154735878537337\GemPhoneFarm Setup.exe` | Stuck cache copy |

### Resolution Steps Executed
1. Verified cloud copy exists and is complete (224,202,335 bytes)
2. Deleted all local copies (4 locations)
3. Deleted backup folder `D:\backup_gdrive_lost_and_found`
4. Cleared `lost_and_found` cache folder
5. Restarted GoogleDriveFS.exe (taskkill + start)
6. Verified clean mount and no new notifications

### Useful Commands
```bash
# Kill and restart
taskkill /F /IM GoogleDriveFS.exe
timeout /t 3
start "" "C:\Program Files\Google\Drive File Stream\130.0.2.0\GoogleDriveFS.exe"

# Check running processes
tasklist /FI "IMAGENAME eq GoogleDriveFS.exe"

# View recent logs
python -c "
import os
log = os.path.expandvars(r'%LOCALAPPDATA%\Google\DriveFS\Logs\drive_fs.txt')
with open(log, 'r', encoding='utf-8', errors='ignore') as f:
    print(''.join(f.readlines()[-50:]))
"

# Check lost_and_found
python -c "
import os
laf = os.path.expandvars(r'%LOCALAPPDATA%\Google\DriveFS\lost_and_found')
for r, d, f in os.walk(laf):
    print(r, d, f)
"
```

### DB Query Templates
```python
import sqlite3

# Metadata DB - check pending operations
conn = sqlite3.connect(metadata_db)
cur = conn.cursor()
cur.execute("SELECT * FROM operations WHERE status != 'completed'")
cur.execute("SELECT * FROM local_stable_ids")

# Mirror DB - check pending uploads/deletes
conn = sqlite3.connect(mirror_db)
for t in ["pending_uploads", "queued_uploads", "pending_deletes"]:
    cur.execute(f"SELECT * FROM {t}")
```

### Account ID Mapping
To find account_id:
```python
import os
base = os.path.expandvars(r'%LOCALAPPDATA%\Google\DriveFS')
for d in os.listdir(base):
    if d.isdigit() and len(d) > 15:  # Google account IDs are long numbers
        print(d)
```

### Version Note
Google Drive File Stream version: 130.0.2.0
Executable: `C:\Program Files\Google\Drive File Stream\130.0.2.0\GoogleDriveFS.exe`