# Remote Admin Node Disk Exhaustion Diagnosis & Safe Farm Media Cleanup

## 1. Symptom & Context
On secondary farm hosts (e.g. Admin PC `192.168.110.119`), disk drives can silently run down to **0 bytes free** (100% full) due to accumulated raw video downloads (`D:\video goc may 2`) and installer binaries in `D:\Downloads`.
This causes desktop applications (such as Riot Client, League of Legends, TFT, Chrome, or ADB loggers) to fail updates with generic UI errors like:
`COULDN'T UPDATE: Something went wrong with the update, even after repairing`

## 2. Root Cause Discovery via Logs
Do NOT guess or attempt random repairs:
1. **Riot Client Launcher Logs:** Inspect `%localappdata%\Riot Games\Riot Client\Logs\Launcher\<latest>.log`.
   Look for executable movement failures:
   ```text
   ALWAYS| Moving running executable: D:\x\Riot Games\Riot Client\RiotClientServices.exe -> D:/x/Riot Games/Riot Client/RiotClientServices.old
   ERROR | Update failed: Failed copying moved launcher: OS error 112: There is not enough space on the disk.
   ```
2. **Drive Capacity Inspection:**
   Query disk free space via WMIC or PowerShell:
   ```cmd
   wmic logicaldisk get caption,freespace,size
   ```
   If `FreeSpace` is `0`, all self-updates and file transactions fail immediately.
3. **Vanguard Service Verification:**
   Ensure Vanguard driver (`vgk`) and service (`vgc`) are properly running:
   ```cmd
   sc query vgk
   sc query vgc
   sc config vgc start= auto
   net start vgc
   ```

## 3. Safe Cleanup Protocol (Preserving Farm Operations)
When the user requests clearing disk space, NEVER delete farm directories blindly. Strictly follow this 2-stage policy:

### Stage 1: Clean Downloaded Installers
Delete stale installer packages in `D:\Downloads` and root `D:\`:
- Extensions: `.exe`, `.msi`, `.rar`, `.tar.xz`, `.zip.crdownload`
- Keep operational scripts, `.ini`, `.xlsx`, or proxy configurations intact.

### Stage 2: Deduplicate Rendered vs Raw Videos
On Taadaa Farm Admin, videos are downloaded raw into `D:\video goc may 2\<folder>\<file>.mp4` and rendered into `D:\TIKTOK-videonuoinick-admin\<folder>\<file>.mp4`.
- **Invariant:** A raw video file `D:\video goc may 2\<folder>\<file>.mp4` is ONLY safe to delete if:
  1. The rendered video `D:\TIKTOK-videonuoinick-admin\<folder>\<file>.mp4` exists.
  2. The rendered file is non-corrupt / non-empty (`size > 100 KB`).
- Running this cross-check reclaims 150–200+ GB safely without deleting unrendered media or interrupting cron sessions.

## 4. Script Delivery Pattern over SSH to Admin
Because `D:\Taadaa\tools` on Kibe is local and may not match the file structure on Admin:
1. Encode cleanup Python scripts as base64.
2. Push and decode into `C:\Users\Admin\AppData\Local\Temp\clean_admin_disk.py` via PowerShell:
   ```powershell
   $b = [Convert]::FromBase64String('<b64>'); [IO.File]::WriteAllBytes('C:\Users\Admin\AppData\Local\Temp\clean_admin_disk.py', $b)
   ```
3. Execute remotely:
   `python C:\Users\Admin\AppData\Local\Temp\clean_admin_disk.py --apply`

## 5. CLI Trailing Backslash Escaping Pitfall
When executing remote shell commands via SSH wrappers or terminal:
- **Trap:** `python admin_ssh_exec.py "dir D:\\"`
- **Why it breaks:** The trailing backslash before the ending double quote (`\\"`) causes MSYS bash and Hermes security parsers to treat `\"` as an escaped quotation mark. The string remains open, triggering syntax errors or `Reason: command parser limit or malformed executable payload` approval prompts.
- **Remedy:** Never leave a trailing backslash inside double quotes. Use forward slashes (`"dir D:/"`) or omit the trailing slash (`"dir D:"`).
