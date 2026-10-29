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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
