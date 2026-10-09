# Full Video Resolution & Video Scale Safety Invariant

## Incident Analysis: The "Teo nhỏ video" (Shrunk Video) Defect
During a canary verification of dubbed video delivery on Telegram, two versions were generated:
1. `canary_clean_preview.mp4`: Downscaled with `-vf "scale=544:960"` to 50% resolution to minimize file size and upload latency (~4MB).
2. `canary_clean_fullres.mp4`: Full original resolution 1088×1920 (~17MB).

**User Feedback**:
"Cái dưới bị teo nhỏ video" — The downscaled preview appeared visibly compressed and small on mobile players, creating an impression of damaged or cropped output even though aspect ratio (17:30) was preserved.

## Hard Rule: Zero Blind Downscaling for Final Delivery
1. **Always deliver Full Native Resolution for Verification Artifacts**:
   - Unless specifically instructed by the user to produce a lightweight preview, NEVER deliver downscaled videos as the primary acceptance artifact.
   - For vertical short-form content (TikTok/Douyin), keep native dimensions (1088×1920 or 1080×1920).
2. **Compression without Resolution Loss**:
   - To reduce file size for quick network transmission, adjust H.264 CRF (`-crf 23` to `26`) and preset (`-preset fast`), rather than downscaling pixels:
     ```bash
     ffmpeg -y -i input.mp4 -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4
     ```
   - This cuts file size significantly while preserving full-screen aspect and crisp subtitles.

## Content-Addressed Caching for Multi-Segment Audio (Cache Collision Pitfall)
During Sol Auditor closeout reviews, a major architectural flaw was surfaced:
- Naming temporary audio files simply by index: `voice_{idx}_raw.wav` causes silent cache collision.
- If a pipeline re-runs on a modified script, reordered lines, or different voice casting in the same temp directory, it mistakenly reuses stale audio files without invoking TTS.
- **Fix**: Always include a content hash of text, speaker, and slot duration:
  ```python
  def compute_segment_hash(text: str, speaker: str, slot_duration: float) -> str:
      key = f"{text}|{speaker}|{slot_duration:.3f}"
      return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
  ```
  File naming: `voice_{idx}_{seg_hash}_raw.wav`. This guarantees cache freshness while preserving idempotent resumes.
