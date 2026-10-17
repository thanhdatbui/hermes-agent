# Hybrid Cloud Storage Video Pipeline & Remote Google Drive Provisioning

## Architecture: Hybrid Media Pipeline (Cold Storage + Local Working Cache)
When managing multi-terabyte media pools (e.g. video rendering farms, raw footage archives) on storage-constrained nodes (e.g. 500GB–1TB local SSDs):

### 1. The Direct Cloud Rendering Anti-Pattern
- **Never render directly across mounted virtual cloud drives (`G:\My Drive` / Rclone mount / DriveFS stream)**.
- Video encoding/rendering tools (FFmpeg, CapCut, Premiere) perform aggressive random seeks and high-bitrate continuous reads across multiple tracks.
- Direct network streaming causes:
  - Render times to explode 5x–10x (e.g. 30s clips taking 5+ minutes).
  - Seek timeouts and I/O buffer starvation.
  - Immediate process crash / abnormal exit on transient WiFi or socket packet loss.

### 2. Render-Gated Source Offload Workflow
To free local SSD space safely without disrupting production render pipelines:
1. **Identify Render Completion ($O(1)$ set intersection)**:
   - Source directory: `D:\video goc may 2\{folder_id}\{video_id}.mp4`
   - Render destination: `D:\TIKTOK-videonuoinick-admin\{folder_id}\{video_id}.mp4`
   - Safe offload candidates: only source files whose corresponding rendered video exists and has non-zero size (`set(src_vids).intersection(ren_vids)`).
2. **Transfer to Cold Storage**:
   - Copy rendered source files to `G:\My Drive\Kho_Video_Goc\{folder_id}\`.
   - Maintain strict 1:1 folder-to-channel structure.
3. **Integrity Gate & Purge**:
   - Confirm cloud copy exists and byte count matches local copy.
   - Delete local source file from SSD.
   - **Purge Windows Recycle Bin**: `Clear-RecycleBin -Force` or equivalent, otherwise deleted gigabytes remain allocated in `$RECYCLE.BIN`.

---

## Remote Headless Provisioning of Google Drive Desktop (Windows via SSH)

### 1. Silent Download and Installation
From remote SSH session:
```cmd
curl -L -o D:\Downloads\GoogleDriveSetup.exe https://dl.google.com/drive-file-stream/GoogleDriveSetup.exe
cmd /c start /wait D:\Downloads\GoogleDriveSetup.exe --silent
```

### 2. Mandatory Pre-Run Cache Redirection (Preventing C: Drive Crash)
Google Drive Desktop defaults cache to `%LOCALAPPDATA%\Google\DriveFS\<account_id>\content_cache` on `C:\`. Uploading large media pools will immediately exhaust `C:\` and crash Windows services.
```cmd
reg add "HKLM\Software\Google\DriveFS" /v ContentCachePath /t REG_SZ /d "D:\GoogleDriveCache" /f
mkdir D:\GoogleDriveCache
```

### 3. Session 0 to Session 1 Interactive UI Bridge (`/it` Flag)
- SSH runs under Windows Session 0 (Services). Running `launch.bat` or `GoogleDriveFS.exe` directly from SSH runs headlessly in Session 0 and will **not** show the sign-in dialog or browser OAuth to the user sitting at the console (Session 1).
- **Solution via Scheduled Tasks with `/it` (Interactive)**:
  ```cmd
  schtasks /create /tn RunGDrive /tr "\"C:\Program Files\Google\Drive File Stream\<version>\GoogleDriveFS.exe\"" /sc once /st 00:00 /f /it
  schtasks /run /tn RunGDrive
  ```
  The `/it` switch instructs Windows to execute the task interactively inside the currently logged-on user's console session, displaying the Google sign-in window and system tray icon.
