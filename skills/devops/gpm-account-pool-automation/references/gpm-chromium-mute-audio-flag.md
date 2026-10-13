# GPM Chromium Audio Muting via addition_args (--mute-audio)

## Background & Problem
When running automated browser sessions (such as background Gmail nurture watching YouTube videos, shorts, or interactive web pages) on farm host machines (e.g., Kibe), remote desktop sessions (RDP, UltraViewer, AnyDesk, RustDesk) transmit system audio to the remote operator by default.
Muting the master volume on Windows often reverts after a PC reboot because Windows audio drivers re-initialize sound endpoints.

## Permanent Solution: Chromium `--mute-audio` Flag via GPM Local API
Chromium provides the standard flag `--mute-audio` which mutes all web contents without interfering with DOM playback APIs (`HTMLMediaElement.play()`, autoplay policies, or view event tracking).

### GPM Local REST API (v3) Integration
In GPMLogin v3, the profile start endpoint `/api/v3/profiles/start/{profile_id}` has a vendor parameter typo (`addination_args` instead of `addition_args`). Passing only `addition_args` causes GPM to silently ignore the flag. Always pass BOTH simultaneously for dual compatibility:
```python
# Query parameter pattern (dual-param compatibility):
url = f"{GPM_API_BASE}/profiles/start/{profile_id}?win_scale=0.8&addination_args=--mute-audio&addition_args=--mute-audio"
res = requests.get(url, timeout=30).json()
```
Or via `GPMClient.start_profile`:
```python
client.start_profile(
    profile_id=profile_id,
    addition_args="--mute-audio"
)
# Inside GPMClient.start_profile:
# params["addination_args"] = addition_args
# params["addition_args"] = addition_args
```

### Invariant & Key Benefits
1. **Survives Reboots:** Attached directly to browser launch arguments, independent of Windows sound card state.
2. **Zero Impact on Automation / Trust:** Nurture scripts and platforms (YouTube, Google) still execute playback metrics and video progress normally.
3. **Resource Savings:** Chromium skips sound card rendering and audio buffer pipelines, saving CPU cycles on multi-profile runs.

### Synchronization Note
When modifying nurture scripts deployed via Hermes cron, ensure synchronization across both local repo and Hermes deployment target:
- `D:/Taadaa/GPM auto/scripts/cron_gpm_gmail_nurture.py`
- `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_gpm_gmail_nurture.py`
