# Expressive Vietnamese TTS backend selection

## Session-derived evidence

The first `douyin-auto-dub` proof used Faster-Whisper + public translation fallback + Edge-TTS + FFmpeg. The resulting MP4s had valid video/audio streams and correct male/female role changes, but the listener reported that the voices were still one-color and lacked acting. This is an observed quality failure of the chosen backend, not a rendering failure.

A direct advisor call through OmniRoute `review` compared the following layers:

- `pnnbao97/VieNeu-TTS`: Vietnamese TTS engine; its README advertises v3 Turbo, Conversation/multi-speaker mode, emotion/non-verbal cues such as `[cười]`, `[thở dài]`, `[hắng giọng]`, and 3–8 second voice cloning. These are README claims until verified by a local A/B audio test.
- `jianchang512/pyvideotrans`: end-to-end video translation/dubbing workflow with ASR, translation, speaker diarization/multi-role dubbing, timing and multiple TTS backends. It is an orchestration layer, not a guarantee of expressive Vietnamese; quality depends on the backend selected.
- `Huanshere/VideoLingo`: strong subtitle cutting/translation/alignment workflow with multiple TTS integrations, but the README notes that the dubbing workflow does not automatically assign a separate voice to each speaker; treat this as a limitation for multi-character Douyin clips.
- `debpalash/VoiceStudio`: broad local voice/video workspace, but GitHub popularity alone is not evidence of better Vietnamese acting or speaker-role dubbing.

## Decision

For this target, evaluate **pyVideoTrans + VieNeu-TTS v3 Turbo** first because it covers the complete video path while allowing a more expressive Vietnamese TTS backend. Keep `D:/Taadaa/douyin-auto-dub` as a narrow adapter/fallback for Douyin-specific preprocessing, batch handling, subtitles, and render integration; do not discard it just because Edge-TTS underperformed.

## Minimal A/B PoC

Use one 30–45 second real dialogue clip with 2 speakers and 8–12 alternating turns. Freeze the transcript and Vietnamese translation across all backends. Include a question, a reaction, a joke, and an emotion cue where supported. Render:

1. current Edge-TTS baseline;
2. VieNeu standalone;
3. VieNeu routed through pyVideoTrans if supported.

PASS requires the listener to identify the two roles without subtitles, distinguish question from statement, perceive the reaction/joke, hear natural pauses, and stay within about 300–500 ms of source turn timing. If two or more criteria fail, reject that backend for this use case.

## Constraints and caveats

- GTX 1660 Ti 6GB / Windows 10: isolate ASR and TTS; start with CPU/ONNX and measure model memory before enabling CUDA.
- Translation quality is a separate variable. Douyin slang, ellipsis, memes, and wordplay can dominate perceived quality, so do not change translation while comparing TTS engines.
- Check model and voice licenses before commercial use. Open-source repository status is not blanket permission for every checkpoint, voice, or dataset.
- Do not report an expressive-quality win from README features or star counts. Only the listened-to target-environment PoC is acceptance evidence.

## Sources inspected

- https://github.com/pnnbao97/VieNeu-TTS
- https://github.com/jianchang512/pyvideotrans
- https://github.com/Huanshere/VideoLingo
- https://github.com/debpalash/VoiceStudio
