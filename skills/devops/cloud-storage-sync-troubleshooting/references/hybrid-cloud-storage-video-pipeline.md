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
### 1. Identify Render Completion ($O(1)$ set intersection with Farm Slot Formula)
- **CRITICAL PITFALL: `f_src` is NOT `f_vid`!**
  Never assume `D:\video goc may 2\{folder_id}` maps to the same `{folder_id}` in `D:\TIKTOK-videonuoinick-admin`. In the Taadaa farm slot mapping (`clean_farm_disk.py`):
  ```python
  MACHINES_PER_SLOT = 80
  SLOTS_PER_MACHINE = 8

  def f_src_to_f_vid(f_src: int) -> int:
      slot = (f_src - 1) // MACHINES_PER_SLOT + 1
      m_idx = (f_src - 1) % MACHINES_PER_SLOT + 1
      return (m_idx - 1) * SLOTS_PER_MACHINE + slot
  ```
  - Example: `f_src=1 -> f_vid=1`, but `f_src=2 -> f_vid=9`, `f_src=3 -> f_vid=17`.
  - Comparing folder `2` directly to render folder `2` will compare two completely different niches/creators!
- **Render Completion Gate (`CLIPS_REQUIRED = 30`)**:
  - Source directory: `D:\video goc may 2\{f_src}\{video_id}.mp4`
  - Render directory: `D:\TIKTOK-videonuoinick-admin\{f_src_to_f_vid(f_src)}\{video_id}.mp4`
  - Rendered clips must be completed files (`> 100 * 1024` bytes).
  - Only offload source files when the rendered folder has at least 30 completed clips (`len(completed) >= 30`).

### 2. Transfer to Cold Storage via Native Robocopy
- Use Windows built-in `robocopy` for high-throughput transfer into Google Drive Desktop Stream mount (`G:\My Drive`):
  ```cmd
  robocopy "D:\video goc may 2\{f_src}" "G:\My Drive\video_goc_backup\{f_src}" /E /NP
  ```
  - Performance: transfers 1.3+ GB in ~3–4 seconds across local DriveFS virtual buffer.
- **Cache Throttling Guard**: Google Drive buffers uploads in `D:\GoogleDriveCache`. If free space on `D:\` falls below safety threshold (e.g. 15GB), pause batch and let DriveFS flush uploads to cloud before copying the next batch.
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

### 4. Interactive OAuth 2.0 Loopback Limitation (Why CLI cannot auto-login)
- Google Drive Desktop requires OAuth 2.0 authorization through an interactive browser.
- The desktop app binds to a random local loopback port (`http://127.0.0.1:<random_port>/`), listens for the authorization code redirect, and requires explicit user consent on the Google Accounts login page (`accounts.google.com`).
- **Coordinator Mandate**: Do NOT attempt blind CLI script loops, synthetic mouse-click scripts, or keystroke injections across headless SSH sessions to bypass the Google OAuth login window. Inform the operator to perform the 15-second browser consent directly in the console session (via AnyDesk/RDP), ensuring the target profile is selected and "Stream files" mode is confirmed.

### 5. Windows Task Scheduler & Virtual Drive `G:\` User Token Boundary
- **Virtual Drive Isolation under SYSTEM**: In Windows, volume mounts created by userland filesystems (DriveFS / Dokan / WinFsp) exist strictly within the interactive logon session of the user who launched them (`Admin`). Scheduled tasks running under `SYSTEM` or non-interactive service accounts will see `G:\` as non-existent (`The device is not ready` or `Path not found`).
- **Required Task Configuration**:
  Always register tasks accessing DriveFS virtual drives with `/ru Admin` and `/it` (interactive mode):
  ```cmd
  schtasks /create /tn Taadaa_Sync_GDrive_Backup /tr "cmd /c python D:\Taadaa\tools\sync_and_clean_gdrive.py 20" /sc hourly /mo 2 /ru Admin /it /f
  ```
- **DriveFS Startup Persistence on Reboot**:
  To guarantee Google Drive FS launches and remounts `G:\` after scheduled multi-cluster reboots (e.g. 05:20, 11:20, 17:20):
  ```cmd
  schtasks /create /tn RunGDrive /tr "\"C:\Program Files\Google\Drive File Stream\132.0.0.0\GoogleDriveFS.exe\"" /sc onlogon /ru Admin /it /f
  ```

### 6. Incremental Verification & Cleanup Script (`sync_and_clean_gdrive.py`)
To prevent SSH command timeouts and guard against cache overflow:
- Structure the batch runner to process folders in bounded chunks (e.g., 10–20 folders per run).
- Verify file sizes byte-for-byte on `G:\` before unlinking local raw `.mp4` files from `D:\video goc may 2`.
- Local disk headroom expands immediately with each completed folder (e.g., in practice recovering 28+ GB in minutes while maintaining cloud synchronization).


