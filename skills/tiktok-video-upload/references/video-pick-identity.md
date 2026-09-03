# Video-Pick Thumbnail Identity Verification

## Problem
`VIDEO_PICK_TARGET_UNVERIFIED` on Tik2 (random-script-render source) while Tik1 ("ông A" render) passes. The picker thumbnail is:
- a 1:1 center crop of a 9:16 source (loses both sides),
- overlaid with a duration badge `00:13`, selection circle, and an emoji sticker baked into the video,
- re-compressed by TikTok.

→ grayscale 64x64 Pearson correlation of tile vs source frame ≈ 0.09-0.14 (threshold 0.35) → fail-closed, even though the tile IS the right video (human-verified).

## Measurement (machine 45, folder 354, source 3.mp4)
| Metric | same video | diff video (same folder) | gap |
|---|---|---|---|
| grayscale corr (64x64) | 0.09-0.14 | 0.03 / -0.03 | narrow |
| **RGB color-histogram intersection** (256 bins/ch, min/sum) | **0.82-0.83** | 0.50-0.68 | **0.14+** |
| 2x2 spatial-histogram (avg of 4 quadrant histograms) | 0.70-0.83 | 0.50-0.66 | 0.10+ |

## Fix (in `state_machine._verify_video_tile_identity`)
1. Keep source frames as **RGB** (not grayscale) so the histogram works.
2. Add `_image_histogram_similarity` (RGB 256-bin per-channel, intersection = Σ min(a,b)/Σa) and `_image_spatial_histogram_similarity` (2x2 grid, average of quadrant intersections).
3. Accept a tile when:
   - correlation ≥ 0.35 AND margin over 2nd candidate, **OR**
   - color-histogram ≥ 0.75 AND margin ≥ 0.05 AND spatial-histogram ≥ 0.68 AND margin ≥ 0.03 AND the spatial winner IS the color winner (same candidate).
4. Return `dict(accepted_candidate)` — the candidate the accepted metric selected. (Bug: returning the correlation winner on the histogram path tapped the wrong tile.)

## Constants
- `VIDEO_PICK_TILE_HISTOGRAM_THRESHOLD = 0.75`
- `VIDEO_PICK_TILE_HISTOGRAM_MARGIN = 0.05`
- `VIDEO_PICK_TILE_SPATIAL_HISTOGRAM_THRESHOLD = 0.68`
- `VIDEO_PICK_TILE_SPATIAL_HISTOGRAM_MARGIN = 0.03`

## Crop gotcha
The picker grid top ~18-39% of 1080x1920 is the "Tất cả / Video / Ảnh" tab bar + duration badge — NOT thumbnail. Crop the actual thumbnail region below the tab bar, or the identity metric compares against UI chrome.

## Tests
- `test_video_pick_histogram_rescues_low_correlation_script_render` — corr low, histogram+spatial high → verify.
- `test_video_pick_histogram_winner_is_tapped_not_correlation_winner` — correlation best=A (<0.35 so corr path fails), histogram+spatial verify B → must return B. (If correlation actually passes, the correlation path wins by design — correct; the test must keep correlation below threshold to exercise the histogram path.)

## Threshold-margin case (machine 7, 2026-08-14) — correct tile, all metrics slightly under
Machine 7 (folder 50, video 50/1.mp4): picker showed the single just-pushed video (a white Ford convertible, red interior) under "Gần đây", and the extracted first frame of 50/1.mp4 matched the tile 1:1 (vision-verified) — push + MediaStore index correct. Yet the workflow logged, on the VERIFY step with true XML bounds:
- corr = 0.243 / 0.174 (threshold 0.40)
- hist = 0.772 / 0.758 (threshold 0.80 + margin 0.05)
- spatial = 0.614 / 0.587 (threshold 0.71)

All three under, histogram/spatial only slightly. This is an OVERLAID/COMPRESSED-tile threshold case, distinct from the wrong-push case. Decision rule for loosening: measure the negative (same tile vs a different machine's folder video) and only loosen if the negative stays clearly below (≥ ~0.15 gap). Do NOT loosen color alone without the spatial guard (audit round-1 rejection reason).

## Naive re-measurement trap (machine 7)
Comparing `video-pick-target-verify.png` (full-screen 1080x1920) directly against the source frame gives corr 0.159 / hist 0.139 — garbage, even though the video is correct, because the artifact is a FULL-SCREEN capture; the tile occupies only the top-left corner region. Manually cropping by eye also fails (0.43 pos / 0.37 neg — crop missed the tile). The ONLY trustworthy numbers are the ones the workflow logs on its ERROR line (`corr=…/…; hist=…/…; spatial=…/…`), computed from XML-derived tile bounds. When a run's XML dump wasn't persisted, re-run with UI capture enabled rather than re-deriving metrics from screenshots.
