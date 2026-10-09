---
name: desktop-performance-diagnosis
description: "Diagnose sudden intermittent Windows desktop/game freezes with onset-first timeline correlation, live reproduction, and fail-closed intervention discipline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, performance, gaming, stutter, freeze, latency, telemetry, root-cause]
    related_skills: [systematic-debugging, desktop-automation, verification-evidence]
---

# Desktop Performance Diagnosis

## Purpose

Use this skill for sudden stutter, freezes, frame-time spikes, audio/input pauses, or intermittent 3–5 second hangs on a Windows desktop—especially when the machine was normal until a specific recent time.

**Core rule:** diagnose the onset and the live symptom before blaming a familiar background application. A process that is resource-heavy now is only a suspect; it is not a cause until its activity aligns with the freeze or a controlled A/B test changes the symptom.

## Scope and safety

- Start read-only: collect event logs, process state, update history, driver/device state, storage/network counters, and application logs.
- Remote Host First: When diagnosing performance on a remote/secondary host (e.g. `admin-farm` / other LAN machines), check configured remote access (`~/.ssh/config`) and query the target machine directly via SSH first. Never speculate from local machine telemetry or local cron schedules when direct remote inspection is accessible.
- Windows OpenSSH Shell Wrapping: Remote Windows OpenSSH servers often default to `cmd.exe`. Always wrap diagnostic one-liners explicitly: `ssh <host> "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"<cmd>\""` to prevent cmd parsing errors (such as `'Sort-Object' is not recognized`).
- Do not kill processes, disable security, pause sync, change drivers, edit registry, change power plans, or reboot while investigating unless the user explicitly authorizes the intervention.
- Do not inspect credentials, mailboxes, workbooks, or unrelated farm data merely because automation processes exist on the host.
- Report unproven correlations as hypotheses, not conclusions.

## Onset-first workflow

### 1. Freeze the contract

Record:

- last-known-good time (for example, "worked yesterday; failed this morning");
- first-known-bad time and whether the issue occurs outside the game;
- exact symptom: rendered picture pause, audio pause, input pause, ping spike, FPS drop, or only client/UI stall;
- frequency and duration (for example, every 30–60 seconds for 3–5 seconds);
- scope: only one game, all 3D apps, or the whole desktop.

The latest user correction about onset supersedes an earlier broad suspicion. If the user says a long-running app has always worked, treat that as evidence against a static incompatibility. Re-open it only for a recent update, cache/state change, or interaction with a changed component.

### 2. Build a bounded change timeline

Search only the onset window first:

- Windows Update and Microsoft Defender intelligence/platform updates;
- GPU/chipset/storage driver changes;
- application install/update timestamps and updater logs;
- service/task starts and scheduled maintenance;
- crash/restart loops (ADB, launchers, overlays, sync clients);
- WHEA, Display, Disk, storahci/stornvme, Kernel-Power, Application Hang/Error, and DNS events;
- files modified in relevant application/log directories.

Do not let a noisy recurring event such as DCOM 10016 dominate the diagnosis unless its timestamp and component behavior align with the symptom.

### 3. Classify the symptom before ranking causes

- **Local frame/system stall:** screen, audio, input, or unrelated apps pause. Prioritize CPU scheduling, GPU/driver, storage/I/O, hardware errors, overlays, and security scanning.
- **Network-only stall:** rendering continues but ping/packet loss rises. Prioritize NIC, DNS, route, VPN/booster, and server path.
- **Game/client stall:** desktop remains responsive and only League/Riot stops. Prioritize game files, Riot client, overlay hooks, and game logs.
- **Automation-induced stall:** the desktop/game freezes near device-control bursts, crash/restart loops, or large I/O bursts. Correlate ADB/Xiaowei and farm activity without assuming it is causal.

Ask the user whether the whole picture freezes. If unavailable, mark the distinction unproven.

### 4. Collect baseline telemetry, then reproduce live

A snapshot while the game is closed cannot prove a game-specific cause. Capture a short live interval while the game is running and the user records each freeze timestamp. At 1-second resolution, sample:

- total CPU and per-process CPU for game, overlays, WebView, Defender, sync, booster, launchers, and automation;
- GPU temperature, utilization, VRAM, engine utilization, and display-driver events;
- physical disk active time, latency/queue, process I/O, pages/sec, and available memory;
- network RTT/packet loss separately from local frame behavior;
- process creation/restart, application errors, WHEA, Display, Disk, and Defender events.

The acceptance condition is timestamp correlation or a controlled A/B result, not merely a high current RAM/CPU number.

### 5. Rank hypotheses with falsifiable predictions

For each candidate, state what would be observed if it were causal:

1. Newly updated component: its update/first-run/cache event falls before the onset and its activity aligns with freezes.
2. Security/sync/I/O: disk queue or process I/O spikes at freeze timestamps, often with Defender/OneDrive activity.
3. Overlay/WebView: disabling only that overlay changes frame-time behavior while the rest of the environment stays constant.
4. Automation/crash loop: ADB/Xiaowei process churn or crash/restart timestamps align with freezes and disappear when that workload is absent.
5. PCIe/GPU/driver: WHEA/Display events, GPU engine stalls, or driver resets align with freezes; absence of events lowers but does not eliminate this hypothesis.
6. Network: RTT/packet loss spikes while local rendering continues; this does not explain a full image/audio/input freeze.

Discard hypotheses that have no observable prediction.

### 6. Use minimal A/B tests only after evidence collection

Change one variable at a time and preserve a baseline. A test such as closing Overwolf, GearUP, OneDrive sync, or an overlay is useful only if:

- the user authorizes that intervention;
- the game is launched under otherwise comparable conditions;
- the result is observed for enough time to cover multiple expected freeze intervals;
- the exact changed component and result are recorded.

Do not close several suspects at once. Do not report an A/B result from a test that was not actually run.

### 7. Hardware escalation

Repeated WHEA PCIe events are a real hardware/firmware signal but are not automatically the cause of a game stutter. First correlate their timestamps and identify the PCIe device/root port. If the symptom persists with low background load and no software correlation, escalate read-only checks of GPU seating/power, chipset/BIOS, PCIe link stability, and storage health before making changes.

## Windows evidence commands

Use PowerShell through the Windows shell runner. Prefer bounded, read-only queries:

```powershell
Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).Date}
Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).Date}
Get-Process | Sort-Object CPU -Descending
Get-Counter '\Processor(_Total)\% Processor Time','\PhysicalDisk(_Total)\Avg. Disk Queue Length','\Memory\Pages/sec'
Get-PhysicalDisk
Get-CimInstance Win32_VideoController
```

When using PowerShell from Git Bash, quote the entire `-Command` payload carefully and avoid nested shell interpolation. If a diagnostic script fails to parse, classify it as a harness failure and rerun with simpler quoting; never treat missing telemetry as evidence of a clean system.

## Remote diagnosis via SSH

When the affected machine is a LAN host with SSH access (e.g. `admin-farm` from `~/.ssh/config`), run all telemetry **directly on the target** — do not speculate from the local machine. Preferred pattern:

```bash
# Quick read-only snapshot — PowerShell via SSH (cmd.exe default, must wrap explicitly)
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, Id, CPU, WorkingSet64 | Format-Table -AutoSize\""

# GPU state
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"nvidia-smi\""

# Disk queue
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"(Get-Counter '\\PhysicalDisk(*)\\Avg. Disk Queue Length').CounterSamples | Format-Table -AutoSize\""

# VRAM + GPU memory
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory\""
```

### Applying fixes via SSH — use scp + `-File`, never inline complex scripts

Inline PowerShell with backticks (`` ` ``) **breaks bash** due to substitution conflicts. For any multi-line or complex fix script:

```bash
# 1. Write the script locally
cat > /tmp/fix.ps1 << 'PSEOF'
# ... PowerShell content with backticks, $vars, etc. ...
PSEOF

# 2. Copy to target
scp /tmp/fix.ps1 admin-farm:"C:/Taadaa_Service/fix.ps1"

# 3. Execute
ssh admin-farm "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\Taadaa_Service\\fix.ps1"
```

### Game config file lock pitfall

Unreal Engine / Riot game client config files (`GameUserSettings.ini`) are **locked by overlay processes** (Overwolf, TFTAcademy, OverwolfBrowser) even when the game itself is closed. The file appears writable but writes silently fail (the `Set-Content` call returns OK but the file is unchanged).

**Fix sequence:**
```powershell
# 1. Kill overlay processes holding the lock
Stop-Process -Name TFTAcademy, Overwolf, OverwolfBrowser, OverwolfHelper, OverwolfHelper64 -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Write using raw bytes (not Set-Content or WriteAllText encoding pitfalls)
$f = "C:\Users\Admin\AppData\Local\TFT\Saved\Config\WindowsClient\GameUserSettings.ini"
$d = [System.IO.File]::ReadAllBytes($f)
$txt = [System.Text.Encoding]::UTF8.GetString($d)
$txt = $txt.Replace("bUseVSync=True","bUseVSync=False")
# ... etc
[System.IO.File]::WriteAllText($f, $txt, [System.Text.Encoding]::UTF8)

# 3. Verify with type not powershell (bypasses PS read cache)
# ssh admin-farm "type `"C:\path\GameUserSettings.ini`" | findstr /i `"vsync`""
```

### User communication style during remote diagnostics

**`??` or `???` in response = user wants the fix applied NOW, not more explanation.** When the diagnosis is clear:
- Skip the analysis writeup
- Execute the fix directly via SSH
- Show one-line confirmation when done

Do NOT: write multi-paragraph explanations of why something is broken after the root cause is established. Do NOT: list what you're about to do before doing it.

## Reporting standard

Keep the user-facing report concise and factual:

- **Observed:** exact timestamps and real counters/events.
- **Strong evidence:** correlations or controlled A/B results.
- **Hypotheses:** ranked, with what remains unproven.
- **Blocker:** what could not be correlated (for example, game was not running).
- **Next test:** one minimal, authorized action.

Do not say "root cause found" when only an idle snapshot or a list of heavy processes exists. Say "current leading hypothesis" and explain the missing live evidence in one sentence.

## References

- `references/desktop-performance-onset.md` — reusable onset timeline, evidence matrix, and interpretation notes from a Windows game-stutter investigation.
- `references/console-window-storm-and-headless-subprocess-disruption.md` — diagnose rapid screen flashing / window storms caused by background automation (e.g. ADB, FFmpeg) missing Windows `CREATE_NO_WINDOW` flags.
- `references/windows-nic-disconnect-repair.md` — diagnostic patterns and repair procedures for NDIS 10400 hardware resets, outdated NIC drivers, and power-saving disconnects under game/VPN load.
- `references/game-input-latency-and-io-stutter.md` — secondary mechanical disk queue thrashing (DPC latency), V-Sync/windowed input lag, Vanguard-protected process inspection, Unreal/Overwolf overlay stalls, Dual Xeon single-thread IPC limits under batch load, GPU VRAM thrashing from multi-overlay CEF apps, and remote SSH host diagnosis.
- `references/game-network-latency-diagnosis.md` — diagnose game network delay vs local freeze, extract server IP from logs, inspect NIC packet buffer discards, and check TCP socket churn.
- `references/ssh-remote-game-config-fix.md` — proven scp+`-File` pattern for applying game config fixes (V-Sync, FullscreenMode, FrameRateLimit) via SSH; overlay file-lock pitfall; Dual Xeon + GTX 1660S VRAM saturation context; nvidia-smi SSH one-liners.
- `references/legacy-32bit-game-memory-crash.md` — diagnose legacy 32-bit game crashes ("Not enough memory resources", Handle2AgentReg, cmemblock), pure PowerShell PE header LAA (0x0020) checks, and 4GB Patch application.
- `references/mystery-startup-console-window-diagnosis.md` — diagnose blank/flashing PowerShell or CMD windows appearing on boot; trace caller via PowerShell Event ID 400 HostApplication, ParentProcessId, Startup registry keys, and Electron app.asar child_process calls lacking windowsHide.

## Pitfalls

- Blaming a familiar app because it consumes RAM/CPU now, despite the user reporting it worked normally before.
- Overlooking Default Gateway Misrouting in dual-router setups: In environments with two routers on the same subnet (e.g. Ruijie FPT for Host PC + MikroTik Viettel for phone farm proxies), a DHCP race or reservation can silently hijack the host's 0.0.0.0/0 route to the farm router. The host's games then exit via the congested farm ISP instead of direct FPT, while app-specific proxies (like TELEGRAM_PROXY on 192.168.110.2:10001) never needed host-level default routing in the first place.
- Confusing colloquial 'delay' (network latency / packet loss) with local input lag / VSync / display stutter, and dismissing network based solely on an ICMP ping to 8.8.8.8.
- Assuming clean ICMP ping to 8.8.8.8 means game networking is healthy: game traffic uses UDP to distinct game servers (Riot VN2/SGP), vulnerable to ISP transit peering drops or NIC buffer overflow.
- Overlooking local automation workloads (ADB streams, multi-worker uploads) flooding host NIC buffers (`Packets Received Discarded`) or exhausting router NAT tables with thousands of `TimeWait` sockets.
- Ignoring secondary drives: assuming a game installed on NVMe SSD cannot lag from disk I/O, missing severe queue thrashing on a secondary SATA HDD (e.g. background orphaned `grep -rn` or batch workers) causing system-wide DPC/interrupt latency and mouse hitching.
- Confusing input lag with network latency: V-Sync + Windowed Fullscreen at 60Hz creates 30–60ms+ mouse delay that users describe as "network delay" despite normal ping.
- Assuming `Get-Process.Path` works for all games: anti-cheat systems (Riot Vanguard `vgk.sys`) strip process query handles, returning null paths unless inspected via registry or known install paths.
- Treating an update from days ago as the cause of a symptom that started this morning without checking the onset window.
- Using WHEA or DCOM events as proof without timestamp correlation.
- Calling a network timeout the cause of a full local freeze without checking whether rendering/audio/input continued.
- Collecting telemetry while the game is closed, then claiming the game-specific cause is proven.
- Fixing before investigation: killing processes, disabling Defender, changing registry/driver/power settings, or rebooting without authorization.
- Bundling multiple A/B changes so no causal conclusion is possible.
- Assuming high core-count workstation/server CPUs (e.g. Dual Xeon 56-thread) can never bottleneck esports/gaming titles: high core count does not compensate for low single-core frequency (e.g. 2.4 GHz) or IPC limits when heavy background workloads (FFmpeg x264 filter-chains, 20-worker batch jobs) contend for L3 cache, memory buses, and CPU time.
- Overlooking GPU VRAM saturation from concurrent Chromium/CEF overlays and Remote Desktop sessions: multiple Electron/CEF apps (Overwolf + TFTAcademy) and active `mstsc.exe` sessions can saturate GPU VRAM (e.g. GTX 1660S reaching >80% VRAM allocation), forcing DirectX swap-chains to spill into PCIe shared system memory and causing severe frame-time spikes/hitching.
- Blaming network routing or farm automation blindly without checking SSH/remote access already available to inspect the target host's live GPU (`nvidia-smi`), background render processes (`ffmpeg`), and overlay memory consumption directly.
- Blaming physical RAM when a 32-bit legacy game crashes with "Not enough memory resources to process this command": 32-bit executables without Large Address Aware (LAA) are hard-capped at 2 GB Virtual Address Space (VAS) on 64-bit Windows regardless of host RAM (e.g. 64 GB physical with 46 GB free). Check `<GameDir>\Errors\*.txt` and inspect the PE Characteristics offset for bit `0x0020` before assuming system RAM or hardware fault.
- Overlooking missing `creationflags=subprocess.CREATE_NO_WINDOW` in background scripts (`pythonw.exe` / cronjobs) when users complain of desktop "nháy nháy liên tục" (flashing/flickering): `pythonw.exe` only hides Python itself; any console binary (`adb.exe`, `ffmpeg.exe`, `curl.exe`) spawned via bare `subprocess.run()` without `CREATE_NO_WINDOW` will allocate and close hundreds of console windows per minute during concurrent batch runs.
- Assuming a mystery blank PowerShell console window popping up on boot is malware, Windows corruption, or farm automation: check PowerShell Event Log ID 400 (`HostApplication`) to trace the exact command and caller. Electron companion/overlay apps (like TFTAcademy) registered in Windows Startup often poll for target processes (e.g. `LeagueClientUx*`) via `powershell -c ...` without `{ windowsHide: true }`, creating empty console windows on desktop boot when the game is not running.
