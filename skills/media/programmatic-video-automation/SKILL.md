---
name: programmatic-video-automation
description: "Programmatic video creation and editing orchestrated by AI agents using Multimodal Vision, FFmpeg, Remotion, and timeline generators."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [video, editing, ffmpeg, remotion, multimodal, gemini, agent-orchestration]
    related_skills: [automated-video-dubbing, vision-evidence-and-gate6-verification, ui-evidence-first]
---
# Programmatic Video Automation & Agent Orchestration

Use this skill when designing, building, or troubleshooting autonomous agent pipelines that analyze, edit, composite, and render short-form or long-form videos through code and multimodal models.

---

## 1. Core Architecture: Programmatic vs GUI Editing

AI Agents (such as Antigravity, Hermes, Claude) do NOT manipulate desktop video editors (Premiere, CapCut) directly. Instead, they operate via a 4-stage **Programmatic Feedback Loop**:

```
[Input Video / Reference Assets]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ 1. Multimodal Inspector (Mắt đọc)                     │
│    • Extract keyframes via FFmpeg O(1) probe.          │
│    • Inspect layout, 9:16 TikTok safe zone, text bounds│
│      using Gemini Pro/Flash (1M-2M context) / Qwen-VL. │
│    • Extract pacing, cut rhythms, color grades.        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Timeline / Recipe Generator (Não lập kế hoạch)      │
│    • Emit declarative JSON/YAML timeline:              │
│      segments, cut points, caption styling, audio mix. │
│    • Parameterize templates instead of freeform code.  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Headless Execution Engine (Tay thực thi)            │
│    • FFmpeg CLI: fast clip splicing, scale 9:16, audio │
│      ducking, hardcoded subtitle burning (.ass/.srt).  │
│    • Remotion (React/TS): motion graphics, dynamic     │
│      kinetic captions, animated charts, web overlays.  │
│    • OpenCV / MoviePy: face-tracking crop & dynamic pan│
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Visual Evidence & Gate 6 Verification               │
│    • Capture sample output frames.                     │
│    • Verify text legibility, UI occlusion, sync errors.│
└────────────────────────────────────────────────────────┘
```

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
