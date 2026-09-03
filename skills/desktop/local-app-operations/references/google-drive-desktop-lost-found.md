# Google Drive for Desktop "Lost and Found" (Bị thất lạc và đã tìm thấy) Troubleshooting

## Symptoms

Google Drive for Desktop (GoogleDriveFS) displays a recurring toast/popup notification:
- **Vietnamese:** *"Có tệp chưa đồng bộ hóa. Một số tệp không thể đồng bộ hóa vì đã được di chuyển đến thư mục 'Bị thất lạc và đã tìm thấy'. Để ngừng nhận thông báo này, hãy di chuyển tệp đó ra khỏi thư mục 'Bị thất lạc và đã tìm thấy'. Nếu ngắt kết nối tài khoản <email>, tệp có thể bị xóa."*
- **English:** *"Files haven't synced. Some files couldn't sync because they've been moved to the 'Lost and found' folder..."*

## Root Cause

When Google Drive for Desktop encounters a synchronization conflict, race condition, or orphaned file (e.g., local write in progress while parent directory is renamed/moved/unsynced in cloud), Drive moves the conflicting local file into its local cache directory:
`%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\`

Drive creates two items in this directory:
1. The orphaned/conflicted file (e.g. `filename.ext`).
2. `lost_and_found_data.txt`: Contains the original virtual path (e.g., `G:\Drive của tôi\Folder\filename.ext`) paired with the local cache path.

As long as files exist in `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\`, the toast notification persists.

## Diagnosis & Resolution Steps

1. **Locate the Lost and Found cache:**
   ```powershell
   Get-ChildItem -Path "$env:LOCALAPPDATA\Google\DriveFS\lost_and_found" -Recurse
   ```
2. **Read `lost_and_found_data.txt`:**
   Inspect the original file path mapping to understand which file was affected and where it was supposed to live.
3. **Verify against destination on virtual drive (e.g., `G:\`):**
   - Check if the file already exists at the destination path on Google Drive.
   - Compare file size / hashes.
4. **Safety Backup:**
   - If the file is needed or unique, copy it to an external backup directory (e.g., `D:\backup_gdrive_lost_and_found\`) or restore it to its target Google Drive folder.
5. **Clear the cache:**
   - Remove the files from `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\`.
6. **Verify Google Drive sync state:**
   - Inspect `%LOCALAPPDATA%\Google\DriveFS\Logs\drive_fs.txt`.
   - Confirm `sync_engine.cc` reports `operation_queue_size: 0` and `change_ids_up_to_date: true`.
