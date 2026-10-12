# GPM Chromium Audio Suppression & CLI Arguments Guide

## Problem & Background
When running automated accounts/profiles in GPMLogin (such as YouTube viewing, TikTok browsing, News reading, or account nurture on worker/farm host machines), audio playback from embedded media or videos can cause significant disruption during remote access (RDP, TeamViewer, RustDesk, UltraViewer).
Furthermore, muting the Windows host or audio driver often resets upon system reboot or driver reload.

## Solution: Browser-Level Audio Muting via GPM Local API
Chromium supports the native command-line flag:
```
--mute-audio
```
When launched with this flag, all tabs and audio output channels in that browser process are muted at the process level without affecting media playback metrics, user gestures, or site interaction events (such as YouTube `video.play()` duration or TikTok scroll telemetry).

## Implementation in GPMLogin API v3

### CRITICAL PITFALL: Vendor Parameter Spelling (`addination_args` vs `addition_args`)
In GPMLogin internal API implementation and vendor documentation (`GPMLogin/app_data/api_doc/api.html`), the parameter to pass custom CLI flags contains a typo:
```
addination_args
```
(Notice the extra "n" in `addination`).
- **If you pass only `addition_args`**: GPMLogin v3 silently ignores it. Chromium will start WITHOUT the flags (e.g. audio will still play).
- **If you pass `addination_args`**: GPMLogin correctly appends the flags to Chrome's command-line arguments.
- **Best Practice (Dual-Param Compatibility)**: Always pass BOTH parameters simultaneously in the query string to guarantee forward and backward compatibility across all GPM builds:
  `?win_scale=0.8&addination_args=--mute-audio&addition_args=--mute-audio`

### 1. Direct HTTP GET endpoint
When invoking the start endpoint:
```
GET /api/v3/profiles/start/{profile_id}?win_scale=0.8&addination_args=--mute-audio&addition_args=--mute-audio
```

### 2. Python Client Wrapper (`GPMClient.start_profile`)
```python
def start_profile(
    self,
    profile_id: str,
    addition_args: Optional[str] = "--mute-audio",
    ...
) -> Dict[str, Any]:
    params = {}
    if addition_args:
        params["addination_args"] = addition_args  # Vendor typo in GPM v2/v3
        params["addition_args"] = addition_args    # Standard spelling fallback
    res = requests.get(f"{self.base_url}/profiles/start/{profile_id}", params=params, timeout=self.timeout)
    return res.json()
```

### 3. Canary Verification Pattern (Process Flags & Vision)
Never assume CLI arguments were accepted just because the API returned `200 OK`. Always verify via:
1. **Process Inspection:** Scan `psutil.process_iter(['name', 'cmdline'])` on the parent Chrome process to assert `--mute-audio` is in `proc.info['cmdline']`.
2. **Runtime Verification:** Connect over CDP via Playwright, navigate to media site, take screenshot.
3. **Vision Inspection:** Use `browser_vision` (or OCR) to verify the screenshot is clean, properly rendered, and free of blocking popups or black screens before claiming Canary Done.

### 3. Telemetry & Closeout Gate Observability
When starting profiles with custom arguments such as `--mute-audio`, emit structured telemetry before launching the profile to satisfy audit gates and operational observability:
```python
url = f"{GPM_API_BASE}/profiles/start/{profile_id}?win_scale=0.8&addition_args=--mute-audio"
log_telemetry_metric("gpm_audio_mute_request", {
    "profile_id": profile_id,
    "mute_audio_requested": "--mute-audio" in url,
    "endpoint": url.split("?")[0]
})
```

### 4. Key Benefits & Invariants
- **Reboot Immunity:** Persists across host machine restarts because the flag is passed on every process launch.
- **Platform Telemetry Safety:** Platform watch-time, cookies, view counts, and engagement are completely unaffected.
- **Resource Optimization:** Reduces CPU usage on worker machines by skipping host audio decoding/mixing pipelines.
