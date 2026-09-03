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
- `references/windows-nic-disconnect-repair.md` — diagnostic patterns and repair procedures for NDIS 10400 hardware resets, outdated NIC drivers, and power-saving disconnects under game/VPN load.

## Pitfalls

- Blaming a familiar app because it consumes RAM/CPU now, despite the user reporting it worked normally before.
- Treating an update from days ago as the cause of a symptom that started this morning without checking the onset window.
- Using WHEA or DCOM events as proof without timestamp correlation.
- Calling a network timeout the cause of a full local freeze without checking whether rendering/audio/input continued.
- Collecting telemetry while the game is closed, then claiming the game-specific cause is proven.
- Fixing before investigation: killing processes, disabling Defender, changing registry/driver/power settings, or rebooting without authorization.
- Bundling multiple A/B changes so no causal conclusion is possible.
