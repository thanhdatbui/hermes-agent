# Multi-Speaker Dialogue Dubbing & Edge-TTS Resilience

## 1. Edge-TTS WebSocket Stability & Retry Pattern

Edge-TTS communicates with Microsoft's speech service over WebSockets. In batch or multi-sentence dubbing, rapid sequential requests frequently trigger:
```
edge_tts.exceptions.NoAudioReceived: No audio was received. Please verify that your parameters are correct.
```

### Root Causes
1. **Transient WebSocket Connection Drops / Rate-Limiting**: Firing requests in tight loops without delay drops the socket handshake.
2. **Unicode Decomposed Normalization (NFKD)**: Decomposed diacritics (e.g. combining acute/grave accents) cause the Azure/Edge parser to fail silently and close the socket without sending audio bytes. Text **must** be standard NFC normalized (`unicodedata.normalize('NFC', text)`).
3. **Voice-Specific Token Glitches & Phrase Collisions**: Occasionally `vi-VN-HoaiMyNeural` or `vi-VN-NamMinhNeural` rejects specific punctuation pairings (e.g. trailing `á?`, multiple `!`) or specific Vietnamese word collocations (e.g. "Anh có làm gì đâu, em cứ nghĩ linh tinh thế!" will fail silently, whereas "Anh đâu có làm gì, tự em nghĩ ra đấy chứ!" succeeds). If retry + NFKD normalization still fails, paraphrase/reword the sentence slightly.

### Robust Retry & Fallback Implementation

```python
import asyncio
import unicodedata
import edge_tts

async def synthesize_segment_robust(
    text: str,
    voice: str,
    output_path: str,
    max_retries: int = 3,
    delay_between_retries: float = 1.0,
    fallback_voice: str = "vi-VN-HoaiMyNeural"
) -> bool:
    # 1. Enforce NFC normalization
    clean_text = unicodedata.normalize("NFC", text).strip()
    
    # 2. Try primary voice with backoff
    for attempt in range(max_retries):
        try:
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(output_path)
            return True
        except edge_tts.exceptions.NoAudioReceived:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay_between_retries * (attempt + 1))
            else:
                break
        except Exception:
            await asyncio.sleep(delay_between_retries)
            
    # 3. Cross-voice fallback if primary voice failed
    if voice != fallback_voice:
        try:
            comm = edge_tts.Communicate(clean_text, fallback_voice)
            await comm.save(output_path)
            return True
        except Exception as e:
            print(f"Fallback voice also failed for '{clean_text}': {e}")
            
    return False
```

---

## 2. Multi-Speaker Dialogue Allocation

For short dramas, comedy skits, or car dialogue clips:
* **Assign Roles**:
  * Male characters / Drivers / Skeptical voices: `vi-VN-NamMinhNeural`
  * Female characters / AI GPS / Playful or teasing voices: `vi-VN-HoaiMyNeural`
* **Timeline Pacing**:
  * Faster-Whisper segments provide exact start/end timestamps.
  * In Vietnamese translation, adapt sentence length to fit within the `(end - start)` duration (approx. 3.5 syllables/sec).
  * In FFmpeg, calculate relative millisecond delay from video clip start:
    `delay_ms = int((segment.start - clip_start) * 1000)`

---

## 3. Audio Ducking & Stereo Delay Filter

```python
# Construct FFmpeg filter_complex for N dialogue clips:
filter_parts = []
mix_inputs = ["[abg]"]

for i, (audio_file, delay_ms) in enumerate(dialogue_clips):
    filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
    mix_inputs.append(f"[a{i}]")

# Lower background audio to 12% to preserve ambiance (engine sound, laughter)
filter_parts.append("[0:a]volume=0.12[abg]")
filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2[aout]")
```

---

## 4. Windows FFmpeg Subtitle Escape Rule

On Windows, the drive colon in `C:\path\subs.srt` conflicts with FFmpeg filter option parsing:
* Convert backslashes to forward slashes: `C:/path/subs.srt`
* Escape the drive colon with a backslash: `C\\:/path/subs.srt`
* Filter string:
  ```
  -vf "subtitles='C\\:/path/subs.srt':force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=30'"
  ```
