# Canary Audio Mixing & Volume Normalization Case Study

## 1. The Incident: Muted & Hallucinated Canary Output
During a live canary test on `douyin-auto-dub`, the rendered MP4 had valid container streams (H.264 video + AAC audio), but the actual user experience was completely broken ("Video gì như lồn v"):
1. **Whisper Hallucination Loop**:
   - The test video was an arbitrary local Vietnamese review video, but the pipeline config had `source_lang: zh`.
   - Whisper attempted to decode non-Chinese speech as Chinese, resulting in degenerate repetition loops:
     - `Làm ơn làm ơn làm ơn làm ơn làm ơn làm ơn...`
     - `9 90% c mở rộng k thở hổn hển`
     - `Khả năng miễn dịch nỗ lực của Ya`
   - These hallucinated phrases triggered subsequent TTS errors (`NoAudioReceived`) on Edge-TTS.

2. **The FFmpeg `amix` Silence Bug (`mean_volume: -53.5 dB`)**:
   - In `renderer.py`, background audio and 38 voice segments were mixed with:
     ```bash
     [abg][a0][a1]...[a37]amix=inputs=38:duration=first:dropout_transition=2[aout]
     ```
   - **Root Cause**: By default, FFmpeg's `amix` filter applies `normalize=1` (`true`), which divides the volume of **EVERY** input stream by the total number of inputs ($N$).
   - With 38 inputs, both the ducked background audio and the voice lines were attenuated by a factor of 38 (~ -31.6 dB attenuation), causing the final audio mean volume to drop to `-53.5 dB` (near-mute).

---

## 2. The Solution: Studio Loudness Normalization

### FFmpeg Filtergraph Fix
Explicitly pass `normalize=0` to `amix` to preserve the original amplitude of each stream without scaling down:
```bash
[0:a]volume=0.20[abg];
[abg][a0][a1]...amix=inputs=N:duration=first:dropout_transition=2:normalize=0[aout]
```

### Loudness Verification Gate (`volumedetect`)
Before presenting any canary artifact to the user, run volume detection:
```bash
ffmpeg -hide_banner -i output.mp4 -af volumedetect -f null NUL 2>&1 | grep -E 'mean_volume|max_volume'
```

- **Muted / Broken Video (normalize=1)**:
  - `mean_volume`: `-53.5 dB` (REJECTED)
  - `max_volume`: `-32.8 dB`
- **Studio Normalized Video (normalize=0 + volume=0.20)**:
  - `mean_volume`: `-21.9 dB` (ACCEPTED: Standard broadcast/social loudness)
  - `max_volume`: `-3.9 dB`

---

## 3. Windows Subtitle Path Escaping Trap
Passing a full Windows path to the FFmpeg `subtitles` filter:
```bash
-vf "subtitles='D:/path/sub.srt':force_style=FontSize=16,..."
```
Can fail with:
`[AVFilterGraph] Error parsing a filter description around: ,OutlineColour=...`
Or misparse `D` as an option key (`original_size`).

**Best Practice**:
Always run FFmpeg from the working directory and provide a **relative path without a drive letter colon**:
```bash
-vf "subtitles='temp/drama_dub/drama_sub.srt'"
```
This bypasses all Windows path colon escaping issues in FFmpeg filtergraphs.
