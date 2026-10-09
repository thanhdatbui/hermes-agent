# Game Input Latency, Secondary I/O Queue Thrashing, and Display Stutter

## 1. Secondary Drive Thrashing & System DPC / Input Delay
- **Symptom**: User complains of "delay", "sluggish mouse", or micro-stutters in game, even when the game is installed on an NVMe SSD (e.g. `C:\`).
- **Mechanism**:
  - Heavy background I/O on a secondary mechanical SATA HDD (e.g. `D:\`), such as orphaned recursive `grep -rn`, broad disk searches, or background automation batch workers, causes extreme queue lengths (`Avg. Disk Queue Length` > 5–15, `% Disk Time` > 500%).
  - SATA controller interrupts and DPC latency spike system-wide. The Windows input subsystem experiences scheduling delays, translating to mouse cursor hitching, delayed click registration, and frame-time variance in the foreground game.
- **Diagnostic Commands**:
  ```powershell
  # Check per-disk queue and latency across ALL physical drives
  Get-Counter '\PhysicalDisk(*)\Avg. Disk Queue Length', '\PhysicalDisk(*)\% Disk Time', '\PhysicalDisk(*)\Avg. Disk sec/Read' | 
      Select-Object -ExpandProperty CounterSamples | Format-Table Path, CookedValue -AutoSize

  # Find orphaned search or background batch processes thrashing disks
  Get-Process | Where-Object { $_.ProcessName -match 'grep|find|rg|python' } | 
      Select-Object Id, ProcessName, CPU, WorkingSet64 | Format-Table -AutoSize
  ```

## 2. V-Sync + Windowed Fullscreen Input Lag (Perceived "Network Delay")
- **Symptom**: Player reports "game delay" or heavy champion/unit movement latency, but network ping is low (<30ms) with 0 packet loss.
- **Root Cause**:
  - In Unreal Engine / DirectX games (e.g. TFT `TFTClient-Win64-Shipping.exe`), having `bUseVSync=True` combined with `FullscreenMode=1` (Windowed Fullscreen / Borderless) on a 60Hz display forces Desktop Window Manager (DWM) composition and frame queue buffering.
  - This introduces 30–60ms+ of pure input latency (mouse-to-render lag), making drag-and-drop, unit repositioning, and shop actions feel delayed.
- **Config Verification**:
  - Check `AppData\Local\<Game>\Saved\Config\WindowsClient\GameUserSettings.ini` (e.g. TFT at `C:\Users\<User>\AppData\Local\TFT\Saved\Config\WindowsClient\GameUserSettings.ini`).
  - Key parameters to inspect: `bUseVSync`, `FullscreenMode`, `FrameRateLimit`.
  - Fix: Turn off V-Sync in-game, set FPS cap to match or exceed monitor refresh rate (or Uncapped), and test Exclusive Fullscreen if available.

## 3. Anti-Cheat Protected Binaries (Riot Vanguard / EasyAntiCheat)
- **Diagnostic Quirk**:
  - Commands like `Get-Process | Select-Object Path` or `wmic process get ExecutablePath` return empty/blank for Vanguard-protected binaries (`TFTClient-Win64-Shipping.exe`, `League of Legends.exe`, `Valorant.exe`) due to driver-level handle stripping (`vgk.sys`).
- **Correct Inspection Technique**:
  - Query the Windows Uninstall registry keys or standard install roots:
    ```powershell
    Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | 
        Where-Object { $_.DisplayName -match 'Riot|League|TFT' } | Select-Object DisplayName, InstallLocation
    ```
  - Locate runtime logs directly under `C:\Users\<User>\AppData\Local\<Game>\Saved\Logs\` or `C:\Riot Games\<Game>\Logs\`.

## 4. Overlay & Engine Stutter Indicators (Overwolf, MetaTFT, Unreal GC)
- **Overwolf / CEF Injection**:
  - Overwolf apps (MetaTFT, tracker overlays) spawn multiple Chromium Embedded Framework processes (`OverwolfBrowser.exe`) and hook directly into DirectX swap chains via `OverwolfHelper64.exe`, increasing frame-time variance during intense board changes.
- **Engine-Level Stalls**:
  - Search engine log (`TFT.log`) for:
    - Periodic GC pauses: `TFTRuntimePerformanceSubsystem: Garbage collection complete - duration: [0.219]` (causes a noticeable 200ms hitch every ~30–50s).
    - Input drop signatures: `TFTDragSubsystem: Dropped without a valid Hovered component` (indicates mouse drag released or dropped mid-stutter).
    - Session reconnect events: `RGIOPGameSession: Display: Received event with state [connected]` (indicates transient server session drops).

## 5. Phone Farm USB Controller Saturation & Live Mirroring Contention
- **Context**: When the PC host simultaneously acts as a gaming workstation and a phone farm controller (e.g. 50–80 Android devices attached via USB hubs):
  - **Live Screen Grid Decoding**: Leaving the farm GUI (Xiaowei, GemPhoneFarm, or multi-scrcpy grid) unminimized on the desktop forces continuous GPU hardware video decode and DWM desktop composition for dozens of concurrent video streams. This starves the foreground game of GPU render queues and VRAM bandwidth.
  - **USB Host Controller Bus Saturation & Polling Jitter**: High-frequency ADB frame streaming, XML dumps, and touch events across cascaded USB hubs saturate xHCI root hub bandwidth and exhaust USB endpoints. This creates physical USB polling latency spikes for USB gaming peripherals (mouse/keyboard), causing unit drags, cursor movements, and skill triggers to feel delayed or dropped.
  - **Scheduled High-Worker Batch Bursts**: Event-driven or cron-scheduled batch tasks (e.g. 20–40 parallel Python/PowerShell workers executing screencap/XML dump loops) generate massive CPU context switching and secondary disk I/O thrashing (`Avg. Disk Queue Length` > 15–20).
  - **Immediate Mitigation**:
    1. Minimize the farm management window (Xiaowei/GemPhoneFarm) to stop live video decoding during gameplay.
    2. Pause or reduce worker concurrency for background automation batch jobs while gaming.
    3. Separate gaming peripherals onto a dedicated native USB controller (e.g. direct motherboard rear I/O port) distinct from the farm's multi-tier USB hub PCIe controller.

## 6. High-Core Server CPU (Dual Xeon) & Single-Thread Gaming IPC Fallacy
- **The Core Count Fallacy**: When a workstation/server host (e.g. Dual Intel Xeon E5-2680 v4 @ 2.40GHz, 28 Cores / 56 Threads) runs a game alongside batch automation (e.g. `ffmpeg` batch rendering from `run_tik*_random_render.ps1`, or 20-worker `download_all_sources.py`):
  - Users assume 56 threads mean the machine "has plenty of room and cannot lag from CPU load".
  - However, esports and DirectX titles (League of Legends, TFT) depend almost entirely on single-core clock frequency and IPC (2.4 GHz on Xeon vs 4.5–5.0+ GHz on modern desktop CPUs) for the main render/game loop.
  - Multi-process background tasks (video encoding filter-complexes, multi-socket downloads) thrash shared L3 cache and saturate RAM memory buses, severely throttling the single-thread IPC of the game engine.
  - The game suffers frame drops, micro-stutters, and perceived input lag even while total CPU utilization sits at a modest 30–45%.

## 7. GPU VRAM Thrashing from Dual Chromium/CEF Overlays and Remote Desktop
- **Overlay & CEF VRAM Saturation**:
  - Running multiple companion overlays simultaneously (e.g. Overwolf/MetaTFT + TFTAcademy) spawns 10–20+ Chromium Embedded Framework processes (`OverwolfBrowser.exe`, `TFTAcademy.exe`), consuming 5–7+ GB of system RAM and allocating gigabytes of dedicated VRAM for hardware-accelerated web views.
  - In combination with active Remote Desktop sessions (`mstsc.exe`), VRAM on 6GB GPUs (such as NVIDIA GeForce GTX 1660 SUPER) frequently exceeds 80–85% allocation.
  - When in-game board transitions, combat rounds, or shop refreshes demand new texture buffers, DirectX is forced to page memory across the PCIe bus to shared system memory, causing sharp 200–500ms visual freezes and dropped drag-and-drop inputs.
  - **Diagnostic Command**:
    ```powershell
    nvidia-smi  # Inspect Memory-Usage percentage and check PID list for CEF apps and mstsc.exe
    Get-Process -Name Overwolf*, TFTAcademy*, mstsc* | Measure-Object WorkingSet64 -Sum
    ```

## 8. Multi-Machine Remote Performance Diagnosis Protocol (SSH to Secondary Hosts)
- **Protocol Rule**: When diagnosing performance or game lag on a secondary cluster/farm machine (e.g. `admin-farm` / `192.168.110.119`), do NOT speculate from the local host or assume local bottlenecks apply.
- Use the configured SSH connection (`ssh admin-farm`) immediately to pull live telemetry:
  1. Inspect interactive user session (Session 1): GUI processes (`LeagueClient`, companion overlays, `mstsc`) reside in Session 1, not Session 0:
     ```powershell
     Get-Process | Where-Object { $_.SessionId -eq 1 } | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 Name, Id, CPU, @{N='WS_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}
     ```
  2. Inspect GPU utilization & VRAM pressure via `nvidia-smi`.
  3. Trace background batch automation pipelines up to their parent scripts via WMI/CIM:
     ```powershell
     $p = Get-CimInstance Win32_Process -Filter "ProcessId = <PID>"; $p.CommandLine; (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.ParentProcessId)").CommandLine
     ```

