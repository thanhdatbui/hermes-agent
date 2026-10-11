# Educational Watermark / Graphic False-Face Trap & Human Avatar Verification

## Overview
During automated avatar extraction for TikTok accounts mapped to non-vlog / educational / infographic niches (e.g., "Học tập", medical slides), automated face detectors (Haar cascades, low-threshold YOLO) can fire false-positive face detections on circular watermark emblems, logos, seals, or diagrams (e.g., the Vietnamese Ministry of Education GDĐT seal: torch, book, globe, text "VÌ SỰ NGHIỆP GIÁO DỤC").

When this happens, the script crops the corner watermark and writes it as `avatar.jpg`, producing an absurd non-human avatar.

## Critical Invariants

### 1. Niche vs. Creator Identity Audit Before Extraction
Before attempting to extract a portrait avatar from channel videos (`D:/video goc/<folder>/`):
- Verify whether the channel videos contain actual camera/selfie footage of a human creator.
- If the folder contains slides, medical diagrams, infographics, or screen recordings, **DO NOT** run automated face crop on the video frames. Video watermark seals will almost certainly be misclassified as faces.
- For human accounts mapped to non-human video niches, use curated human creator portrait pools (e.g., `D:/Taadaa/avatar_options/`) or request the designated human avatar source.

### 2. Strict Anti-Hallucination Vision Verification Rules
Before reporting avatar readiness or syncing `avatar.jpg`:
- **Actively search for graphic/seal artifacts:** Specifically check for text rings, circular borders, torch/book graphics, crests, emblems, cartoon illustrations, or diagrams.
- **Verify organic human anatomy:** Confirm genuine skin texture, eyes, pupils, nostrils, lips, hair strands, and lighting gradient. An illustrated face or emblem with circular geometry must NOT be accepted as a human portrait.
- **Deliver candidate comparison (`square + circular crop`):** Generate side-by-side previews (`square 512x512` alongside `circular crop 512x512`) and inspect both with vision before uploading.

### 3. Dual-Verification Pipeline
```
[Video Source] 
       │
       ▼
Is Video Human Vlog/Selfie? ──No──► DO NOT EXTRACT. Use curated human creator pool.
       │ Yes
       ▼
Extract Candidate Frame
       │
       ▼
Vision Inspection: Check for Emblems/Logos/Graphic Badges
       │ Passed (Real human face confirmed)
       ▼
Crop & Resize Lanczos4 512x512 (Center Face, 45-55% circle area)
       │
       ▼
Sync Dual Stores (video goc & TIKTOK-videonuoinick) -> Queue PENDING
```
