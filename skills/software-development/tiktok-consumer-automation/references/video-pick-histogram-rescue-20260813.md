# VIDEO_PICK histogram rescue — measurement recipe & evidence (2026-08-13)

## Context
Tik2 videos (source = script-random render) fail `VIDEO_PICK_TARGET_UNVERIFIED` though the
pushed video is correct. Grayscale-64x64 correlation collapses (~0.13) when TikTok's picker
thumbnail is center-cropped 1:1 with overlay (duration badge `00:13`, progress ring) and
heavy compression — even when the scene is identical (vision confirms match).

## Metric that works: RGB color-histogram intersection (PIL-only)
`cv2/numpy/scipy` are NOT available in the automation venv — do not use ORB/SIFT.

```python
from PIL import Image

def hist_sim(a, b):
    ha = a.convert("RGB").resize((128, 128)).histogram()
    hb = b.convert("RGB").resize((128, 128)).histogram()
    n = len(ha) // 3
    score = 0.0
    for ch in range(3):
        ea = [x / (sum(ha[ch*n:(ch+1)*n]) or 1) for x in ha[ch*n:(ch+1)*n]]
        ob = [x / (sum(hb[ch*n:(ch+1)*n]) or 1) for x in hb[ch*n:(ch+1)*n]]
        score += sum(min(x, y) for x, y in zip(ea, ob))
    return score / 3.0
```

Crop the tile from `video-pick-grid.png` using real bounds (approximately y=350..700,
357x357); do not compare `video-pick-target-verify.png` directly because that artifact is
full-screen 1080x1920. Extract source frames with ffmpeg at 0.0, 0.15, 0.35, 0.6, 0.85,
and 1.5 seconds.

## Measured values (machine 45, video 354/3.mp4 vs same-folder negatives)

| Comparison | hist_sim |
|---|---|
| SAME video (3.mp4) | 0.824-0.828 |
| DIFF 1.mp4 | 0.576-0.613 |
| DIFF 5.mp4 | 0.676-0.681 (closest) |
| DIFF 10.mp4 | 0.089-0.581 |
| DIFF 20.mp4 | 0.504-0.558 |
| grayscale correlation | 0.09-0.18 |

Gap SAME vs max-DIFF = 0.14 → threshold 0.75 + margin 0.05 separates this measured set.

## Implemented fix
- `_image_histogram_similarity` (PIL): RGB histogram intersection, 32 bins/channel.
- `_video_frame_tile_histogram` and `_tile_histogram_to_frames` parallel the correlation path.
- `_verify_video_tile_identity` accepts either correlation (`>=0.35`, margin `>=0.05`) or
  histogram (`>=0.75`, margin `>=0.05`); both remain fail-closed.
- `_video_source_frames` keeps RGB frames (correlation converts internally).
- Config keys: `video_pick_tile_histogram_threshold` / `_margin`.

## Pitfalls
- `video-pick-target-verify.png` is full-screen, not a tile crop.
- Mock `_tile_histogram_to_frames` alongside `_tile_similarity_to_frames` in tests; sort
  scored tuples with `key=lambda item: item[0]` to avoid comparing candidate dicts on ties.
- `tests/*.py` use CRLF; Python `str.replace` with LF-only anchors will not match. Preserve CRLF.
- Baseline stash: `pre-video-pick-histogram-fix-20260813` was created before the fix.
