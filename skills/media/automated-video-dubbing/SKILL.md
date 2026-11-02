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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
