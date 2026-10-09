# Repo scaffold and verification notes (2026-10-05)

## Canonical scaffold

Repo: `D:\Taadaa\douyin-auto-dub`

Expected runtime pieces:

- `douyin_dub/transcriber.py`: Faster-Whisper timestamps and audio extraction.
- `douyin_dub/translator.py`: provider chain with an offline/mock provider for tests.
- `douyin_dub/synthesizer.py`: Edge-TTS segment generation.
- `douyin_dub/renderer.py`: delayed voice tracks, ducked original audio, SRT generation and FFmpeg rendering.
- `douyin_dub/pipeline.py`: single-video and batch orchestration.
- `cli.py`: `dub` and `batch` commands.
- `tests/test_modules.py`: mocked unit coverage.

## Verification recipe

Run from the repo root, not from the parent workspace:

```bash
python -m pytest tests/
python cli.py --help
python cli.py dub -i "C:/path/input.mp4" -o "C:/path/output.mp4"
ffprobe -v error -show_entries stream=codec_name,codec_type,duration -of json "C:/path/output.mp4"
```

Acceptance evidence from the scaffold bring-up:

- `python -m pytest tests/`: 13 passed in about 1.3 seconds.
- `cli.py --help`: exposes `dub` and `batch`.
- Real short-video CLI smoke test produced an MP4 with H.264 video and AAC audio.

## Edge-TTS lesson

`NoAudioReceived` can be transient and can also be triggered by specific Vietnamese Unicode/punctuation combinations. The reliable implementation pattern is:

1. Send the original NFC/precomposed text first.
2. Retry up to a bounded count with a short backoff.
3. On retry, use `unicodedata.normalize("NFKD", text)` if the provider rejects the original form.
4. Keep tests asserting the original text on the first attempt; otherwise a test can fail even though the production fallback is useful.

Do not claim TTS quality or full end-to-end correctness from mocked tests alone. A real CLI render plus `ffprobe` is required to prove the artifact has both streams.

## Scope and evidence

The worker summaries were incomplete/time-limited, so inspect the worktree and run the commands yourself before reporting completion. For code changes, run the focused test command in the same verification window after the final edit. Keep provider/network failures separate from code failures.
