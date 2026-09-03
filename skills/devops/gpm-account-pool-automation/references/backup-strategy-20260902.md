# GPM Backup Strategy - Session 2026-09-02

## OneDrive Backup Structure
Location: `D:\OneDrive\backup\GPM\`

| File | Size | Description |
|------|------|-------------|
| `gpm_active_16profiles_20260901.zip` | 3.54 GB | 16 quan trọng profiles: AMZ_Main + 15 farm phones (GroupId 7, 9) |
| `gpm_hidden_240profiles_20260901.zip` | 7.80 GB | 240 hidden profiles (GroupId = 0, deleted via API mode=1) |
| `profile_data.db` | 1.46 MB | Raw SQLite DB metadata for all 256 profiles |

## Commands Used

### 1. Create backup list for active profiles (16)
```python
import sqlite3, os
conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
cur = conn.cursor()
cur.execute('SELECT Name, ProfilePath FROM Profiles WHERE GroupId IN (7, 9);')
# Write paths to backup_list.txt
```

### 2. Compress with 7za (from GPM install dir)
```bash
# Active profiles
7za a -tzip -mx3 -ssw D:\OneDrive\backup\GPM\gpm_active_16profiles_20260901.zip @backup_list.txt

# Hidden profiles (240)
7za a -tzip -mx1 -ssw D:\OneDrive\backup\GPM\gpm_hidden_240profiles_20260901.zip @deleted_profiles_list.txt
```

### 3. Copy raw database
```bash
copy "C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db" "D:\OneDrive\backup\GPM\profile_data.db"
```

### 4. iCloudDrive selective mirror to OneDrive
```bash
# Target: D:\OneDrive\backup\iCloudDrive\data\
# Include folders: Amazon*, MAIl, BOOKS, rua, tools, x, Trading, Downloads
# Exclude: .Trash, Cache, Browser, script, iCloud~*, F3LWYJ7GM7~*
robocopy "C:\Users\Kibe\iCloudDrive" "D:\OneDrive\backup\iCloudDrive\data" /E /R:1 /W:1 /XF desktop.ini /XD .Trash Cache Browser script
```

## Google Drive Desktop Setup
```bash
# Install
winget install --id Google.GoogleDrive -e --silent --accept-source-agreements --accept-package-agreements

# Executable
C:\Program Files\Google\Drive File Stream\130.0.2.0\GoogleDriveFS.exe

# Config: Settings → Folders from your computer → Add folder → D:\OneDrive → Sync with Google Drive
```

## GPM Profile Storage Locations
- **Database**: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
- **Backup DB**: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\_backup\profile_data_backup.db`
- **Profile folders**: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\{ProfilePath}\`
- **Total size**: ~31 GB for 256 profiles
- **S3Path column**: All NULL (no cloud sync configured)

## GPM Cloud Sync Options
1. **Private Server Addon** (~2M VNĐ) - GPM managed cloud
2. **Self-hosted S3/R2/MinIO** - Configure Access Key + Secret Key in GPM Settings
3. **Current**: No cloud sync, relying on OneDrive + Google Drive backup