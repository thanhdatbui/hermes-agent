# SSH Remote Game Config Fix — Proven Patterns

## Context
Fixing Windows game/client settings (Unreal Engine `GameUserSettings.ini`) on a remote LAN
machine (e.g. `admin-farm` at `192.168.110.119`) via SSH without physical access.

Confirmed working: TFT (Teamfight Tactics) on Dual Xeon E5-2680v4 + GTX 1660 SUPER, Sep 2026.

---

## Problem: V-Sync + Windowed Fullscreen causing 30–65ms input lag

GameUserSettings.ini defaults that cause "delay" perceived as network lag:
```ini
bUseVSync=True
FullscreenMode=1        # 0=Fullscreen, 1=Windowed Borderless, 2=Windowed
PreferredFullscreenMode=1
FrameRateLimit=0.000000 # 0 = uncapped, but VSync clamps to 60Hz = 1-frame buffer lag
```

### Fix values
```ini
bUseVSync=False
FullscreenMode=0
PreferredFullscreenMode=0
FrameRateLimit=144.000000
```

---

## Execution pattern — scp + `-File` (avoid inline PS backtick hell)

```bash
# Step 1: write PS fix script locally (no bash escape issues)
cat > /tmp/fix_tft.ps1 << 'PSEOF'
Stop-Process -Name TFTAcademy -Force -ErrorAction SilentlyContinue
Stop-Process -Name Overwolf -Force -ErrorAction SilentlyContinue
Stop-Process -Name OverwolfBrowser -Force -ErrorAction SilentlyContinue
Stop-Process -Name OverwolfHelper -Force -ErrorAction SilentlyContinue
Stop-Process -Name OverwolfHelper64 -Force -ErrorAction SilentlyContinue
Write-Host "Killed overlays"
Start-Sleep -Seconds 2

$f = "C:\Users\Admin\AppData\Local\TFT\Saved\Config\WindowsClient\GameUserSettings.ini"
$txt = [System.IO.File]::ReadAllText($f)
$txt = $txt.Replace("bUseVSync=True","bUseVSync=False")
$txt = $txt.Replace("FrameRateLimit=0.000000","FrameRateLimit=144.000000")
$txt = [System.Text.RegularExpressions.Regex]::Replace($txt, "FullscreenMode=1`r`n", "FullscreenMode=0`r`n")
$txt = $txt.Replace("PreferredFullscreenMode=1","PreferredFullscreenMode=0")
[System.IO.File]::WriteAllText($f, $txt, [System.Text.Encoding]::UTF8)
Write-Host "File written OK"
Select-String $f -Pattern "VSync|FrameRateLimit=|FullscreenMode="
PSEOF

# Step 2: copy and run
scp /tmp/fix_tft.ps1 admin-farm:"C:/Taadaa_Service/fix_tft.ps1"
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\Taadaa_Service\\fix_tft.ps1"
```

### Verify
```bash
ssh admin-farm "type \"C:\\Users\\Admin\\AppData\\Local\\TFT\\Saved\\Config\\WindowsClient\\GameUserSettings.ini\" | findstr /i \"vsync framerate fullscreen\""
```

Expected output:
```
FrameRateLimit=144.000000
bUseVSync=False
FullscreenMode=0
PreferredFullscreenMode=0
```

---

## Why file writes silently fail without killing overlays

Riot Vanguard + Overwolf + TFTAcademy hold open file handles on the config even after TFT.exe exits.
`Set-Content` and `WriteAllText` return exit code 0 but the file is unchanged on disk.

Diagnostic: `type <file> | findstr ...` will still show old values after a supposedly successful write.
Fix: kill all overlay PIDs first, then write.

---

## Dual Xeon gaming performance context

- **Xeon E5-2680 v4**: 14 cores × 2 CPUs = 56 threads, base 2.40 GHz, turbo 3.3 GHz
- **GTX 1660 SUPER**: 6 GB VRAM — saturated quickly by Overwolf (CEF) + TFTAcademy + mstsc sessions
- **VRAM threshold**: >80% VRAM → DirectX spills to PCIe shared memory → severe frame time spikes
- **Single-core IPC bottleneck**: Esports clients (TFT/LoL) are 1–2 core workloads; 56 threads do not help
  when those 2 cores compete with FFmpeg render workers for L3 cache and memory bus

### Typical concurrent loads seen to cause lag:
- `download_all_sources.py --parallel 20` (yt-dlp batch)
- `run_tik3_random_render.ps1 -Parallel 1` (ffmpeg x264 filter-complex, spawned per machine slot 201–280)
- 4× `mstsc.exe` sessions (each allocates GPU frame buffers)
- Overwolf + TFTAcademy × 20 processes (CEF Chromium, each ~150–300 MB VRAM)

### Quick check via nvidia-smi over SSH:
```bash
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"nvidia-smi\""
# Look for: Memory-Usage column — if >80% of 6144MiB, VRAM is the bottleneck
```
