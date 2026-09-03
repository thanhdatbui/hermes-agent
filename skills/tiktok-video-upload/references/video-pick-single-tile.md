# Video-pick threshold-margin case — machines 7/8 (2026-08-14)

Context: after the histogram+spatial fallback fix (COMPAT-VIDEO-PICK-001), machines 7/8 still
failed `VIDEO_PICK_TARGET_UNVERIFIED` on their FIRST video (folder 50 / folder 58).

## Proven facts
- The pushed video was **correct**: extracted first frame of `D:\TIKTOK-videonuoinick\50\1.mp4`
  matched the picker tile 1:1 (white Ford convertible, red interior — same car in both).
- MediaStore index was right: picker showed the single just-pushed video under "Gần đây"
  (tab Video active), duration badge 00:26.
- Workflow log metrics (trustworthy — computed with real tile bounds from UI XML):
  - attempt 1: `corr=0.243/None; hist=0.772/None; spatial=0.614/None`
  - attempt 2: `corr=0.174/None; hist=0.758/None; spatial=0.587/None`
- Thresholds at the time: corr ≥0.40, hist ≥0.80, spatial ≥0.71 (all with margins).
  → correct video, ALL metrics under threshold; hist/spatial only slightly under.

## Gotchas discovered while investigating
1. **Do NOT measure by comparing `video-pick-target-verify.png` (full-screen 1080x1920)
   against a source frame.** Naive full-image corr/hist gives ~0.14-0.16 for the CORRECT
   video — the tile is a small corner region of that capture. Use the workflow's logged
   metrics instead (or crop with real tile bounds from the UI XML dump).
2. Hand-cropping the tile blind (e.g. `crop((0,200,420,900))`) also gives garbage
   (hist 0.42 pos / 0.37 neg) — crop bounds must come from the XML, not eyeballing.
3. Before loosening any threshold, measure the NEGATIVE (same tile vs a different video
   from another machine's folder). Only loosen if negative sits clearly below
   (gap ≥ ~0.15). A color-only loosen without spatial margin re-opens the
   false-positive class the audit rejected.

## Resolution — superseded by COMPAT-VIDEO-PICK-002
The threshold investigation became moot: the user pointed out that the gallery is cleaned
before push, so the picker holds exactly ONE video tile → tap it directly without any
identity verification (see SKILL.md section). Multi-candidate pickers still run
`_verify_video_tile_identity` (fail-closed preserved).
