# Modular Factory & Farm Batch Dubbing Operations

## Context
When scaling automated dubbing on consumer hardware (e.g. GTX 1660 Ti 6GB / Windows 10), balancing expressive acting quality with batch throughput requires a resilient modular architecture.

## 1. Modular Voice Factory Pattern
Do not bind the pipeline directly to a single TTS provider. Implement an abstract `BaseVoiceProvider` with an auto-fallback factory:

```text
Pipeline
   │
   ▼
VoiceSynthesisFactory
   ├── Primary (VieNeu-TTS v3 Turbo, emotion tags)
   └── Fallback (Edge-TTS, 0-cost baseline)
```

- **Primary failure triggers**: Timeout (>10s), CUDA OOM (>4.5GB VRAM limit), model loading failure, or missing token support.
- **Fallback behavior**: Silently fall back to Edge-TTS (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`) with mapped SSML rate/pitch. Log warning, but never fail the whole batch.

## 2. Emotion Tagging Matrix
Translate contextual cues into engine tokens:

| Tag | Intended Acting | VieNeu-TTS v3 | Edge-TTS Fallback |
| :--- | :--- | :--- | :--- |
| `[cười]` / `[vui]` | Giggling, chuckling, bright tone | Native `[cười]` token | `rate: +10%`, `pitch: +2Hz` |
| `[thở dài]` / `[buồn]` | Heavy exhale, sombre pace | Native `[thở dài]` token | `rate: -15%`, `pitch: -2Hz` |
| `[gắt]` / `[tức giận]` | Sharp, tense, elevated volume | High pitch & rate | `rate: +15%`, `pitch: +3Hz` |
| `[thì thầm]` | Secretive whisper | Low gain/energy | `volume: -40%`, `rate: -10%` |

## 3. Dynamic Timing Aligner (FFmpeg atempo)
Vietnamese translations are frequently 15–30% longer in syllable count than original Chinese source phrases.
- Calculate duration discrepancy: `delta = actual_audio_duration - original_time_window`.
- If `delta > 0.3s`, apply FFmpeg `atempo` filter:
  `tempo_factor = min(1.3, actual_audio_duration / original_time_window)`
- This prevents sequential voice lines from overlapping or colliding while keeping pitch intact.

## 4. Farm Batch Idempotency & Checkpoints
For headless farm workers processing dozens of videos:
- Store intermediate artifacts under `temp/<video_id>/`:
  - `audio_16k.wav` (Whisper extraction)
  - `transcript.json` (STT segments)
  - `translated.json` (LLM Vietnamese translation + emotion tags)
  - `segments/line_*.mp3` (Synthesized audio files)
  - `subtitles.srt` (Timestamped subtitles)
- On batch resume, check for existing artifacts. Skip already completed phases to prevent redundant compute.
- Limit Whisper to CPU `compute_type: int8` to keep GPU VRAM dedicated to TTS and video rendering.
