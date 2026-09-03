# VIDEO_PICK fail-closed identity gate — machine 74 (2026-08-11)

Session detail for COMPAT-VIDEO-PICK-001. Repo: `D:\Taadaa\Tiktok-video`.

## Symptom / root cause

- `video_path = D:\TIKTOK-videonuoinick\585\7.mp4` was pushed and indexed by the
  Android media provider (evidence: `content query` row), but the TikTok picker
  accessibility tree does NOT expose filenames, and the `Download`/`Tải xuống`
  album is not exposed on this build.
- Old fallback chain: `_find_newest_video_tile(xml)` (top-left bounded
  FrameLayout with o79/n8g child) or `_find_visual_video_tile()` (duration
  overlay score) → tapped the tile at (180,546) → selected an OLD video, not
  `7.mp4`.
- Heuristic selects "a video tile", never "the pushed video's tile". No identity
  proof existed anywhere in the chain.

## Fix shape (fail-closed)

```
Download opened?
  yes → _wait_for_element(text=video_name) exact filename; missing → fail-closed
  no  → media provider indexed? (else fail)
      → candidates: _video_tile_candidates(xml)  [bounds from grid j6k/iht + o79/n8g;
                                                   Samsung single-tile fallback 300-520px]
        OR (XML empty) _duration_overlay_regions(screenshot)  [duration overlay = filter ONLY]
      → _verify_video_tile_identity(candidates, video_path, artifact=...)
          frames = _video_source_frames(video_path)
          for each candidate (sorted top,left): best = max over frames of
              _video_frame_tile_similarity(frame, tile_crop)
          PASS iff best >= threshold AND (single OR best - second >= margin)
      → else _fail_video_pick_unverified(...) → context.error = [VIDEO_PICK_TARGET_UNVERIFIED] ...; return False
```

## Constants (StateMachine class)

- `VIDEO_PICK_TILE_SIMILARITY_THRESHOLD = 0.35`
- `VIDEO_PICK_TILE_SIMILARITY_MARGIN = 0.05`
- `VIDEO_PICK_TARGET_UNVERIFIED = "VIDEO_PICK_TARGET_UNVERIFIED"`
- Config overrides: `video_pick_tile_similarity_threshold`, `video_pick_tile_similarity_margin`.
- Similarity: `_image_correlation` = grayscale 64x64 LANCZOS Pearson correlation,
  zero-variance → MAE fallback (shared `_correlate_values`; avatar path unchanged,
  32x32 ring-masked via `_avatar_source_similarity`).

## `_video_source_frames` (ffmpeg subprocess)

- Needs `ffmpeg`/`ffprobe` on PATH (or config `ffmpeg_path`/`ffprobe_path`).
- Timestamps: `{0.0, 0.15, 0.35, 0.6*duration, 0.85*duration}` — dense EARLY
  sampling is load-bearing: within-video temporal correlation measured as low as
  **0.468** on a fast-cut video (1.mp4 frame@50% vs @85%), while cross-video can
  reach 0.899. Thumbnails usually come from the first ~1s.
- Extraction: `ffmpeg -ss <t> -i <src> -frames:v 1 -q:v 4 out.jpg`; temp dir under
  `tempfile.mkdtemp`, cleaned in `finally`. Any failure → `[]` → fail-closed.

## Threshold validation measurements (must redo for other niches)

On folder 585 (machine 74 source), 32x32 vs 64x64, 5 dense timestamps:

| pair | 32px | 64px |
|---|---|---|
| 7.mp4 self (max over different timestamps) | 0.997 | 0.993 |
| 7.mp4 vs 6.mp4 (cross max) | 0.866 | 0.859 |
| 7.mp4 vs 5.mp4 | 0.886 | 0.875 |
| 7.mp4 vs 4.mp4 | 0.855 | 0.849 |
| 7.mp4 vs 8.mp4 | 0.861 | 0.849 |

Decision: threshold 0.35 + margin 0.05, 64px (margin ~0.13). For a fast-cut video
the self-match floor is the risk; dense early timestamps + max-over-frames covers it.

## Tests added (all in TestStateMachine, pass with `PYTHONPATH=`)

- `test_video_pick_ambiguous_grid_fails_closed_without_tap` — 2 tiles, scores
  [0.70, 0.68] → handler False, `taps == []`, sentinel in `context.error`.
- `test_video_pick_taps_only_source_verified_tile` — scores [0.30, 0.75] → taps
  ONLY (536,535) (tile 2), NOT (182,535), completes pick flow → True.
- `test_video_pick_visual_fallback_fails_closed_on_ambiguous_identity` —
  `_find_visual_video_tile(video_path=...)` with 2 overlay regions, [0.72, 0.70] → None.
- `test_video_pick_visual_fallback_requires_source_identity_not_duration` —
  [0.30, 0.75] → returns right tile center (540,525) + similarity 0.75 (not top-left).
- `test_video_pick_fails_closed_when_source_frames_unavailable` — frames [] → False,
  sentinel, no taps.

Tests inject via monkeypatch: `_video_source_frames`, `_tile_similarity_to_frames`
(side-effect list in (top,left) candidate order), `_media_provider_has_target`,
`_find_visual_video_tile`. Transport writes a real PNG for `_capture_video_pick_surface`.

## Legacy-compat invariants

- `_find_newest_video_tile(xml)` still returns `{"center": ...}` top-left candidate
  (shape kept; existing tests assert exact dict).
- `_find_visual_video_tile()` with NO `video_path` keeps the old duration-overlay
  single-row pick (exactly the machine-74 heuristic) — unit-test-only path, never
  reachable from `_handle_video_pick` (always passes `video_path=video_path`).
- `_avatar_source_similarity` behavior unchanged after `_correlate_values` extraction.

## Verification workflow used

1. RED: 5 tests written first → all failed (AttributeError: feature missing).
2. GREEN: implementation → 5 passed; targeted 37 passed; full suite **344 passed**
   (baseline 339).
3. Live measurement on the actual machine-74 file (read-only local, no device).
4. Ad-hoc verification script `hermes-verify-*` under `%TEMP%` exercising the
   changed methods directly → 12/12, deleted after run.
