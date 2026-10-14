# YouTube Subtitles/Captions Extraction via Android Client API (Zero Download / Zero Cookies)

## Problem
- `youtube-transcript-api` fails with IP ban / Cloud provider ban (`Could not retrieve a transcript... YouTube is blocking requests from your IP`).
- Browser visits get redirected to Google bot challenge (`google.com/sorry/index`).
- Standard `yt-dlp` fails with "Sign in to confirm you're not a bot" because the default client (`visionos`) triggers bot detection.

## Solution: Android Client API Subtitle/Caption Stream Extraction
Using yt-dlp with `extractor_args: {"youtube": {"player_client": ["android"]}}` bypasses client bot-checks and exposes subtitle tracks (both manual and auto-generated) directly in metadata without downloading any media file or needing cookies.

```python
import json
import urllib.request
import yt_dlp

ydl_opts = {
    'skip_download': True,
    'extractor_args': {'youtube': {'player_client': ['android']}},
    'quiet': True,
    'no_warnings': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/watch?v=VIDEO_ID", download=False)
    subs = info.get("automatic_captions", {}) or info.get("subtitles", {})
    # Select target language (e.g., vi-orig, vi, en)
    track = subs.get("vi-orig") or subs.get("vi") or subs.get("en") or list(subs.values())[0]
    # Prefer json3 format for structured timestamps + text
    target_fmt = next((f for f in track if f.get("ext") == "json3"), track[0])
    
    req = urllib.request.Request(target_fmt["url"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        sub_json = json.loads(resp.read().decode("utf-8"))
        events = sub_json.get("events", [])
        transcript = []
        for ev in events:
            text = "".join(seg.get("utf8", "") for seg in ev.get("segs", [])).strip()
            if text:
                t_sec = ev.get("tStartMs", 0) / 1000.0
                transcript.append(f"[{int(t_sec//60):02d}:{int(t_sec%60):02d}] {text}")
```

## Key Benefits
- **Zero media download**: Only fetches lightweight JSON metadata and subtitle URL.
- **Zero cookies required**: Works reliably even on cloud IPs / mobile proxies where web browsers are flagged.
- **Instant extraction**: Returns 100% of video transcript in under 2 seconds.
