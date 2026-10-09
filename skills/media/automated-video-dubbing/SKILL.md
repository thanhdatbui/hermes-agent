---
name: automated-video-dubbing
description: "Use when dubbing Douyin/TikTok videos to Vietnamese."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [video, dubbing, douyin, tiktok, edge-tts, whisper, ffmpeg, tts]
    related_skills: [youtube-content, windows-native-ocr]
---

# Automated Video Dubbing Pipeline (Douyin/TikTok to Vietnamese)

Use this workflow to automatically translate and dub foreign short-form videos (Douyin, TikTok, YouTube Shorts) into Vietnamese at zero API cost, high speed, and batch scalability.

---

## Architecture: Lightweight Hybrid vs Heavyweight Local GUI

| Component | Full Suite (pyVideoTrans / VideoLingo) | Narrow Adapter (This Skill / `douyin-auto-dub`) |
| :--- | :--- | :--- |
| **Primary Use** | End-to-end ASR, translation, diarization, multi-role dubbing, alignment and render. | Douyin-specific preprocessing, batch orchestration, subtitle handling and pluggable TTS/render backend. |
| **Vietnamese acting quality** | Depends on the selected TTS backend; the suite itself does not guarantee expressive Vietnamese. | Edge-TTS is clear and cheap but should be treated as a baseline, not an acting-quality solution. |
| **Hardware / VRAM** | Depends heavily on ASR, diarization and TTS engine; test CPU/ONNX before assuming 6GB VRAM is enough. | Lightweight when using CPU Whisper + FFmpeg + remote/Edge TTS; local expressive models may change the footprint substantially. |
| **Automation** | GUI and/or CLI depending on the project; useful when rebuilding the whole workflow is unnecessary. | Headless Python/FFmpeg CLI, suitable for controlled batch processing and adapter experiments. |

---

## Expressive TTS Decision Gate & 80/20 Acting Roadmap

When a user reports that the generated dub is "one color", robotic, or lacks acting ("chưa có diễn xuất nghe chán"), do not keep tuning Edge-TTS pitch/rate blindly. Pitch only shifts tone frequency and rate only shifts speed; neither creates psychological acting, gasp, laughter, or emotional tension.

### 80/20 Hybrid Acting Workflow (Fastest ROI without heavy infra)
Do not immediately discard or rewrite the entire pipeline. Test with an 80/20 tiered rollout:
1. **80% Baseline Dialogue**: Keep Edge-TTS (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`) for routine descriptive dialogue and narrations (zero cost, stable diacritics).
2. **20% Retention Anchors (Hook 3s & Climax)**:
   - Inject Sound FX in editing/CapCut (sighs, laughs, dramatic pauses, gasp/shock sound effects) around punchlines and opening hooks.
   - Or replace only the first 1–2 hook lines with an expressive voice (VieNeu-TTS with emotion tags, MiniMax Speech, or cloned character voice).
3. **Voice Director Layer in Prompting**: In the translation step, instruct LLM to break sentences into short conversational phrases, insert explicit pause markers, and avoid bookish/written Vietnamese.

### Full Backend Evaluation Order
Treat full engine replacement as a systematic backend-selection problem:

1. **Confirm the failure with a real artifact**: listen to a 30–45 second two-speaker clip with 8–12 alternating turns. A valid sample must contain actual dialogue, stable speaker mapping, subtitles, and audio/video streams; do not use a monologue or a music-only beauty clip as evidence.
2. **Separate claims from proof**: README features such as emotion tags, conversation mode, or voice cloning are hypotheses until the same script is rendered and listened to on the target Windows/GPU environment. Never claim a new engine is more expressive before this A/B test.
3. **Recommended evaluation order**:
   - Primary: evaluate a full workflow such as `pyVideoTrans` with an expressive Vietnamese backend (for example VieNeu-TTS v3 Turbo) because ASR, translation, speaker roles, timing, and rendering are already integrated.
   - Fallback: keep `douyin-auto-dub` as the Douyin-specific adapter and replace only the TTS backend, rather than discarding downloader, preprocessing, subtitle, and batch/render code.
   - Do not select by GitHub stars alone; VoiceStudio, VideoLingo, and pyVideoTrans solve different layers of the problem.
4. **A/B acceptance criteria** (same transcript and translation for every backend): the listener can identify speaker roles without reading subtitles, distinguish question vs statement, perceive the intended reaction/joke, hear natural pauses, and the dub stays within roughly 300–500 ms of the source turn. Fail a backend if at least two of these criteria fail.
5. **Hardware gate**: on a GTX 1660 Ti 6GB / Windows 10, isolate ASR and TTS stages, prefer CPU/ONNX for the first PoC, and do not assume Whisper + diarization + expressive TTS can coexist in VRAM. Measure the actual model footprint before adopting CUDA.
6. **Translation is an independent gate**: Douyin slang, ellipsis, memes, and wordplay can make translation—not TTS—the main quality bottleneck. Hold the translation fixed during TTS comparisons, then improve translation separately.

For the advisor-backed comparison of full suites versus Vietnamese expressive backends, keep the evidence and source claims in `references/expressive-tts-backend-selection.md`. For the tested local repo and closeout evidence, see `references/repo-scaffold-verification-2026-10-05.md`.
```
[Input Video MP4]
       │
       ▼
1. Speech-to-Text & Timestamps (Faster-Whisper, model='base' or 'small')
       │
       ▼
2. Contextual Vietnamese Translation (LLM prompt tailored for TikTok/viral style)
       │
       ▼
3. Neural Voice Synthesis (Edge-TTS via vi-VN-HoaiMyNeural)
       │
       ▼
4. Audio Ducking & Hardcoded Subtitles (FFmpeg filter_complex) ──► [Output Dubbed MP4]
```

---

## Step-by-Step Implementation

### Step 1: Extract Audio & Transcribe Timestamps with Faster-Whisper
```python
import subprocess
from faster_whisper import WhisperModel

def transcribe_clip(video_path: str, lang: str = "zh"):
    # Extract mono 16kHz audio for whisper
    wav_path = "temp_audio.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav_path],
        capture_output=True, check=True
    )
    # CPU with int8 is fast (~1-2s for 15s clip)
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(wav_path, language=lang)
    
    timed_lines = []
    for s in segments:
        timed_lines.append({
            "start": s.start,
            "end": s.end,
            "duration": s.end - s.start,
            "text": s.text.strip()
        })
    return timed_lines
```

### Step 2: Translate with Natural Spoken Vietnamese
Translate Chinese/English transcript into concise spoken Vietnamese matching speech length:
* Avoid literal machine translation (e.g. Meta NLLB / Google Translate).
* Keep syllable count approximately matching the original duration (average 3–4 syllables per second).

### Step 3: Generate Vietnamese Audio via Edge-TTS
```python
import asyncio
import edge_tts

async def synthesize_voice_lines(translated_lines: list):
    # CRITICAL: Use vi-VN-HoaiMyNeural for stability with Vietnamese diacritics
    for idx, item in enumerate(translated_lines):
        out_file = f"line_{idx}.mp3"
        comm = edge_tts.Communicate(item["vn_text"], "vi-VN-HoaiMyNeural")
        await comm.save(out_file)
        item["audio_path"] = out_file
```

### Step 4: Mix Audio Timeline & Burn Subtitles with FFmpeg
Duck the original background audio to 10–15% volume, delay each voice line to its start timestamp, and burn subtitles:

```python
import subprocess

def render_dubbed_video(video_path: str, timed_audio: list, srt_path: str, output_path: str):
    # Build adelay filter for each voice segment (in milliseconds)
    inputs = ["-i", video_path]
    filter_parts = []
    amix_inputs = ["[abg]"]
    
    for idx, item in enumerate(timed_audio):
        inputs.extend(["-i", item["audio_path"]])
        input_idx = idx + 1
        delay_ms = int(item["start"] * 1000)
        filter_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[a{idx}];")
        amix_inputs.append(f"[a{idx}]")
        
    # Attenuate background audio to 15-20% and mix with normalize=0 to avoid volume attenuation by N inputs
    filter_parts.append("[0:a]volume=0.20[abg];")
    filter_parts.append(f"{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:duration=first:dropout_transition=2:normalize=0[aout]")
    
    filter_complex = "".join(filter_parts)
    
    # Subtitle burn styling (Windows path escaping requires C\\:/...)
    escaped_srt = srt_path.replace(":", "\\:").replace("\\", "/")
    vf_filter = f"subtitles='{escaped_srt}':force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=30'"
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-vf", vf_filter,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, check=True)
```

## Multi-speaker dialogue quality gate

A two-speaker dub is not automatically expressive just because it uses a male voice and a female voice. Before presenting a sample, require:

1. The source actually contains dialogue between at least two people (not a monologue, music-only beauty clip, or unrelated compilation).
2. The transcript has alternating speaker turns or a manually verified dialogue mapping.
3. Each turn is assigned a stable voice role; do not merely alternate voices blindly when the source speaker does not change.
4. Vietnamese lines are shortened to fit their timestamp window; avoid adding long prose that overruns the original turn.
5. Review the real artifact by listening, not only by checking that FFmpeg produced an MP4. State clearly that Edge-TTS changes timbre and basic prosody, but does not provide true acting/emotion control; stronger emotion requires SSML/prosody controls or a more expressive TTS engine.

For a quick proof sample, use a source with short back-and-forth turns, render at least 30 seconds, and report the exact voices, turn map, subtitle/audio status, and known limitations.

## Strict Canary Acceptance Gate (Chống báo PASS mù / Video rác)

Never claim Canary PASS merely because `ffprobe` shows H.264 video and AAC audio streams! A rendered MP4 can have valid streams but be completely broken (muted, hallucinated gibberish, or language mismatched). Before reporting a canary video to the user, enforce 5 mandatory checks:

1. **Source Language & Dialogue Verification**:
   - Check detected language from Whisper info before dubbing. If `source_lang: zh` is forced on a non-Chinese video, Whisper hallucinates severe degeneration loops.
   - Confirm the video contains actual spoken conversation, not EDM background music with no speech.
2. **Hallucination / Degeneration Gate**:
   - Scan transcribed/translated segments for repetitive token loops (e.g. *"Làm ơn làm ơn làm ơn..."*, *"9 90% c mở rộng k thở..."*).
   - If repetitive phrases exceed 3 identical repetitions, flag `TRANSCRIPT_HALLUCINATED` and halt — do not proceed to TTS and render.
3. **TTS Coverage Gate**:
   - At least 90% of speech segments must successfully synthesize non-zero audio files.
   - If TTS errors (`NoAudioReceived`) cause missing audio lines, ducking will attenuate background audio into silence with zero voice, resulting in a near-muted video.
4. **Volume Detection Gate (`volumedetect`)**:
   - Run: `ffmpeg -i output.mp4 -af volumedetect -f null NUL 2>&1 | grep -E 'mean_volume|max_volume'`
   - Healthy dialogue audio: `mean_volume` must be between `-24 dB` and `-14 dB`, and `max_volume` between `-3 dB` and `0 dB`.
   - If `mean_volume < -35 dB` (e.g. `-53.5 dB`), audio mixing/ducking has muted the video — reject immediately.
5. **Audibility Check**:
   - Coordinator must inspect volume and subtitle alignment before claiming success; never substitute valid container metadata for verified human audibility.

## Ready-to-Use Scripts & Reference Guides

- **Canonical repo scaffold**: `D:\Taadaa\douyin-auto-dub` (CLI: `python cli.py dub -i in.mp4 -o out.mp4` / `python cli.py batch -i in_dir -o out_dir`). The repo contains `transcriber`, `translator`, `synthesizer`, `renderer`, `pipeline`, CLI, and mocked tests.
- **In-repo architecture & operational docs**:
  - `docs/ARCHITECTURE.md`: Modular Factory (`BaseVoiceProvider`), VieNeu-TTS v3 Turbo primary + Edge-TTS fallback, emotion tagging matrix (`[cười]`, `[thở dài]`), dynamic timing aligner.
  - `docs/WORKFLOW_ROADMAP.md`: 5-phase transition from flat reader to expressive multi-speaker production pipeline.
  - `docs/FARM_OPERATION.md`: Batch farm operations, idempotency checkpoints, hardware boundaries (GTX 1660 Ti VRAM < 4.5GB), troubleshooting matrix.
- After edits, verify in the repo root with `python -m pytest tests/` and a real CLI smoke test on a short local video; confirm the output with `ffprobe` has both video and audio streams. A worker self-report or old test count is not evidence for the current tree.
- See `scripts/pipeline_dub.py` for a fully functional, headless end-to-end Python pipeline.
- See `references/canary-audio-mixing-and-volume-normalization.md` for FFmpeg `amix` volume normalization (`normalize=0`), volume detection gates, and Whisper hallucination prevention.
- See `references/video-resolution-and-cache-safety.md` for full-resolution delivery rules (avoiding "video bị teo nhỏ"), CRF optimization, and content-addressed audio caching.
- See `references/vieneu-production-hardening-and-closeout.md` for content-addressed audio cache hashing, zero-leak original audio mute policy, full-res preview delivery rules, and real FFmpeg integration test patterns for closeout audit.
- See `references/modular-factory-and-farm-operations.md` for Voice Factory architecture, emotion matrix mapping, FFmpeg dynamic timing formulas, and idempotent farm checkpoints.
- See `references/multi-speaker-dialogue-and-edge-tts-retry.md` for multi-character dialogue assignment, Edge-TTS WebSocket backoff retries, Unicode normalization rules, and audio ducking formulas.

---

## Real-video Canary Acceptance (mandatory)

A successful `ffmpeg` exit code or an MP4 containing H.264/AAC is only an encode check, not a dubbing PASS. Before accepting a canary on the actual video:

1. **Source gate:** use a source whose spoken language matches `source_lang` and contains real dialogue. Do not force `zh` on an unknown/non-Chinese clip; validate detected language and inspect a transcript sample first.
2. **Coverage gate:** use `faster-whisper` with `word_timestamps=True` (and VAD where useful) to capture short interjections, not only coarse long segments. Every detected speech interval must have a translated/TTS segment or be explicitly marked as non-speech. A 10-segment render can still miss short lines; the accepted 35-second drama canary required 17 dialogue intervals.
3. **Original-audio gate:** for a Vietnamese-only dub, mute the original speech track or reduce it to a negligible level. Ducking to 15–20% can leave foreign speech audible and is not acceptable when the user requires Vietnamese-only speech. Use `volume=0` when the source speech is not separated from music.
4. **Timing gate:** compare each generated audio duration with its source slot. Apply bounded `atempo` only when needed; report slot, actual duration, and applied factor. Do not claim lip-sync from `adelay` alone.
5. **Audio gate:** use `amix=normalize=0` when mixing multiple generated voices, run `volumedetect`, and reject near-silent output. Verify the voice is audible in a phone-speaker-like preview.
6. **Artifact gate:** inspect/listen to the full output and a preview; run `ffprobe` for streams and durations. Report separate statuses for `encode`, `speech coverage`, `foreign-audio suppression`, `timing`, and `human listen`. Only call the canary PASS when all required gates pass.

Proven local shape: Faster-Whisper `small`/`int8` + `zh` + word timestamps → reviewed Vietnamese localization with stable speaker roles → VieNeu-TTS preset voices/emotion cues → per-segment timing adjustment → original speech muted → FFmpeg render → `ffprobe` + `volumedetect` + human listen. Keep transcript and translation frozen for backend A/B comparisons.

## Proven Canary Workflow (VieNeu-TTS v3 Turbo — Đã nghiệm thu thực chiến)

Workflow sau đây đã được nghiệm thu thành công trên video Douyin drama 35 giây. Áp dụng trực tiếp cho batch production.

### Stack chính thức:
- **ASR**: `faster-whisper small + int8 + word_timestamps=True` — bắt đủ các câu ngắn (< 1s), không sót interjection.
- **TTS Engine**: `VieNeu-TTS v3 Turbo` — ONNX CPU, 0 VRAM, RTF ~0.65x, 48kHz Hi-Fi.
- **Voice Map**: Nam → `Thiện Minh`, Nữ → `Trúc Ly`. Truyền đúng `voice_id` (không kèm dấu ⭐ hay mô tả dài).
- **Emotion Tags**: Chèn `[cười]`, `[thở dài]` trực tiếp trong chuỗi text trước khi gọi `tts.infer()`.
- **Dynamic Timing**: Đo `actual_duration` bằng `ffprobe`, nếu `actual > slot + 0.15s` thì ép `atempo=min(1.35, actual/slot)`.
- **Audio Mute Policy**: Tắt hẳn audio gốc (`volume=0`) để loại bỏ tiếng nói nước ngoài. Nếu giữ tiếng động nhạc nền thì dùng `volume=0.04` (4%) tối đa.
- **amix**: BẮT BUỘC `normalize=0`. Không có `normalize=0` → amix chia âm lượng theo số đầu vào → video gần như câm.
- **FFmpeg subtitle path**: Dùng đường dẫn tương đối không có dấu `:` (`subtitles='temp/subdir/file.srt'`), chạy từ `cwd=repo_root`.
- **Output format**: Render full resolution (không scale nhỏ), `libx264 + crf=23 + movflags=+faststart`, xuất trực tiếp để gửi.

### Script tham chiếu:
`D:\Taadaa\douyin-auto-dub\temp\render_full_drama.py` — Script canary đã chạy xong, chứa toàn bộ logic từ TTS → Dynamic Timing → amix → render đầy đủ 17 câu thoại.

### Thông số nghiệm thu:
- Video gốc: 1088×1920, 35s, tiếng Trung (`zh`)
- Bản lồng tiếng: `canary_douyin_full_dubbed_no_chinese.mp4`, `canary_clean_fullres.mp4`
- mean_volume: -24.4 dB | max_volume: -5.4 dB — nghe rõ trên loa điện thoại
- User feedback: **"Có vẻ ổn r đó"** (accepted)

## Engine Wiring Pattern (VieNeu as Default Engine in CLI)

When nối VieNeu vào `DubbingPipeline` và `cli.py` làm mặc định:

### Kiến trúc chuẩn
1. **`douyin_dub/config.py`** — `TTSConfig.engine` default phải khớp với `config.yaml`:
   ```python
   @dataclass
   class TTSConfig:
       engine: str = "vieneu"        # Must match config.yaml default
       voice: str = "vi-VN-HoaiMyNeural"  # Edge-TTS default kept for fallback tests
   ```
2. **`config.yaml`** — đặt engine và voice mặc định cho production:
   ```yaml
   tts:
     engine: "vieneu"
     voice: "Trúc Ly"
   ```
3. **`douyin_dub/pipeline.py`** — nhánh vieneu với comprehensive runtime fallback & telemetry:
   ```python
   engine = getattr(self.config.tts, "engine", "vieneu")
   if engine == "vieneu":
       t0 = time.time()
       try:
           from .pipeline_vieneu import run_dubbing
           # ... call run_dubbing, log completion with telemetry metrics
           return str(output)
       except Exception as exc:
           elapsed = time.time() - t0
           logger.warning(
               "[DubbingPipeline] vieneu engine failure (%s: %s) after %.2fs, falling back to edge-tts engine",
               type(exc).__name__, exc, elapsed
           )
   # falls through to edge-tts synthesizer path
   ```
4. **`cli.py`** — thêm cờ `--engine`:
   ```python
   parser.add_argument("--engine", default=None, choices=["vieneu", "edge"])
   # In _pipeline_from_args:
   if getattr(args, "engine", None):
       config.tts.engine = args.engine
   ```

### Pitfall quan trọng — Dataclass default phải khớp config.yaml
Nếu `TTSConfig.engine = "edge"` nhưng `config.yaml` đặt `engine: vieneu`, thì:
- Tests tạo `Config()` không qua `load_config()` sẽ mặc định route vào vieneu, gọi TTS thật, lỗi `ModuleNotFoundError: No module named 'vieneu'`.
- Phải cập nhật các tests pipeline cũ để tường minh đặt `config.tts.engine = "edge"` khi muốn test luồng edge-tts.
- **Quy tắc:** Dataclass default và config.yaml PHẢI luôn đồng bộ engine mặc định.

### Fallback test pattern (chứng minh robustness — Bắt buộc cả ImportError và RuntimeError)
Reviewer Sol/Opus yêu cầu chứng minh cả 2 kịch bản lỗi:
```python
def test_pipeline_vieneu_fallback_to_edge_on_import_error(monkeypatch, tmp_path, caplog):
    config = Config()
    config.tts.engine = "vieneu"
    pipeline = DubbingPipeline(config)
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if "pipeline_vieneu" in name:
            raise ImportError("Simulated missing vieneu dependency")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    res = pipeline.process_video(str(input_video), str(out_video), ...)
    assert "falling back to edge-tts engine" in caplog.text

def test_pipeline_vieneu_fallback_on_runtime_render_error(monkeypatch, tmp_path, caplog):
    config = Config()
    config.tts.engine = "vieneu"
    pipeline = DubbingPipeline(config)
    def failing_run_dubbing(**kwargs):
        raise RuntimeError("GPU OOM or render pipeline failed")
    monkeypatch.setattr("douyin_dub.pipeline_vieneu.run_dubbing", failing_run_dubbing)
    res = pipeline.process_video(str(input_video), str(out_video), ...)
    assert "vieneu engine failure (RuntimeError" in caplog.text
```

---

## Critical Pitfalls &amp; Solutions

| Pitfall | Root Cause | Fix |
| :--- | :--- | :--- |
| `edge_tts.exceptions.NoAudioReceived` | Rapid sequential requests over WebSocket, decomposed Unicode (NFKD), or specific punctuation combos (`á?`, trailing `!`). | Keep original NFC text for the first request; retry transient failures with bounded backoff, then normalize to NFKD only as a fallback. Do not normalize before the first mocked/normal request because it changes Vietnamese combining characters. |
| Missing speech in downloaded Douyin videos | Many Douyin dance/model/beauty channels only feature trending EDM music with zero spoken dialogue. | Preflight videos by checking detected language and speech character count with `WhisperModel('tiny')` before routing to dubbing. |
| CTranslate2 missing `cublas64_12.dll` on Windows | `faster_whisper` with `device="cuda"` requires matching CUDA 12 runtime DLLs. | Default to `device="cpu"` with `compute_type="int8"` for short video clips; it completes in <2s without GPU dependencies. |
| FFmpeg `subtitles` filter failing on Windows paths | Unescaped Windows drive colon (`C:\path\sub.srt`) is interpreted by FFmpeg as filter parameter delimiter. | Escape drive colon as `C\\:/path/sub.srt` and use forward slashes. |
| Subtitle & voice duration mismatch | Vietnamese translation is often longer than original Chinese text. | In the LLM translation prompt, explicitly request: *"Dịch ngắn gọn, xúc tích, độ dài tương đương câu gốc để vừa thời lượng nói"*. |
| FFmpeg `amix` mute / volume drop (`-53.5 dB`) | Default `amix` has `normalize=1` (true), which divides all input streams by N inputs. With 10–40 segments, voice tracks are divided by 10–40, dropping audio volume to near-silent (`mean_volume: -53.5 dB`). | BẮT BUỘC đặt `normalize=0` trong `amix`: `amix=inputs=N:duration=first:dropout_transition=2:normalize=0`. Kết hợp `volume=0.20` trên stream nhạc nền để giữ âm lượng giọng đọc chuẩn studio (-20 dB đến -24 dB mean volume, max volume > -5 dB). |
| FFmpeg Windows subtitle filter colon parsing error | Windows drive letter colon `D:/path/sub.srt` gets parsed by FFmpeg filtergraph as option key `D` or fails on commas in `force_style`. | Chuyển sang đường dẫn tương đối không chứa dấu hai chấm `subtitles='temp/drama_dub/drama_sub.srt'` hoặc escape nghiêm ngặt. |
| Async TTS in synchronous execution | `edge_tts.Communicate.save()` is async; calling `asyncio.run()` when an existing loop is running raises `RuntimeError`. | Use `asyncio.run()` with fallback to `asyncio.get_event_loop().run_until_complete()` to handle both standalone scripts and environments with active event loops. |
| Zero-Cost Translation Fallback | Single endpoint failures or rate limits on public translation services. | Implement a fallback chain: Google Translate public endpoint (`gtx`) -> MyMemory public API -> preserve original text, with timeouts and user-agent headers. |
| Edge-TTS acting ceiling ("giọng đọc đều, thiếu diễn xuất") | Edge-TTS is trained for neural news/reading, not actor roleplay; pitch/rate cannot produce emotion. | Use 80/20 hybrid: keep Edge-TTS for body lines, add CapCut Sound FX / pauses at punchlines, or route key hook lines through an expressive engine (VieNeu-TTS / MiniMax / voice clone). |
| Mistaking Gemini Pro for TTS solution | Google One AI Premium ($20/mo) has no TTS audio export button on web; Gemini TTS is an API/Studio feature where free tier suffices. | Never advise buying Gemini Pro for TTS; keep Google AI Studio Free for scripts and use Edge-TTS / CapCut for zero-cost voice synthesis. |
| `uv` path parsing error on Windows drive letters (`/d/...` -> `C:\d`) | Passing MSYS POSIX path `/d/Taadaa/...` to native Windows `uv` creates directories on `C:\d` instead of `D:\`. Cleaning with `rm -rf /c/d` trips safe guards and panics user. | Always pass relative paths or native Windows paths (`D:\Taadaa\...`) to `uv venv` and `uv pip` on Windows. Never run destructive `rm -rf` on root drive prefixes. |
| `uv pip install` timeout during large wheel downloads | Downloading large ML packages (sea-g2p 26MB, llvmlite 40MB, gradio 30MB) hits foreground 60s timeout. | Run `uv pip install --link-mode=copy <pkg>` in background with `terminal(background=True, notify_on_complete=True, timeout=180)` to avoid timeout kills. |
| Terminal lifecycle guard crash on Windows venv Python (`embedded null character in path`) | Direct command path `.venv/Scripts/python.exe` causes `lifecycle_guard` to scan Windows PE binary as a shell script and crash with `ValueError: open: embedded null character in path`. | Prepend venv to PATH instead: `export PATH="/d/Taadaa/douyin-auto-dub/.venv/Scripts:$PATH" && python ...` |
| False Canary PASS from valid `ffprobe` streams on muted/failed video | FFmpeg succeeds in creating an MP4 with H.264+AAC streams even when TTS failed and audio ducking reduced volume to silence (`mean_volume: -53.5 dB`). | Never accept stream presence as success. Run `volumedetect` gate (`mean_volume` must be between `-24 dB` and `-14 dB`) and verify human audibility. |
| Sót tiếng Trung còn lọt vào output dù đã lồng tiếng | Whisper coarse segments (10 đoạn lớn) bỏ sót các câu thoại ngắn < 1s xen giữa. Kết quả: 17 câu thoại thật nhưng chỉ render 10, 7 câu còn lại vẫn phát tiếng gốc. | Đặt `word_timestamps=True` để Whisper trả về timestamps ở mức word. Scan toàn bộ kết quả đủ số câu (so sánh với chiều dài clip) trước khi chuyển sang TTS. Đặt `initial_prompt` là câu mẫu của nội dung đích để giảm hallucination. |
| `TTSConfig.engine` dataclass default không khớp `config.yaml` | Đặt `engine: str = "edge"` trong dataclass nhưng `config.yaml` đặt `engine: vieneu`. Tests tạo `Config()` không qua `load_config()` route vào vieneu thật → `ModuleNotFoundError`. | Dataclass default VÀ config.yaml BẮT BUỘC cùng engine (`vieneu`). Cập nhật mọi test cũ về edge-tts để tường minh gán `config.tts.engine = "edge"`. |
| "Cái dưới bị teo nhỏ video" | Xuất preview nhỏ (`scale=544x960`) để giảm dung lượng gửi Telegram, nhưng người dùng nhận nhầm là output chính thức. | KHÔNG bao giờ scale nhỏ output chính. Giảm dung lượng bằng cách tăng CRF (`-crf 23`) hoặc preset nhanh hơn (`-preset fast`). Luôn thêm `-movflags +faststart`. Tách rõ "bản preview gửi Telegram" vs "bản chính thức full-res". |
| VieNeu-TTS preset voice name lookup error (`Voice '...' not found`) | `list_preset_voices()` returns `(label, voice_id)`. Passing the full label with decorative stars/descriptions (e.g. `⭐ Adam bựa — Nam...`) causes key lookup failure. | Pass the exact `voice_id` (tuple element 1, e.g. `'Thiện Minh'`, `'Trúc Ly'`, `'Hải Đăng'`) to `infer(voice=...)`. |
