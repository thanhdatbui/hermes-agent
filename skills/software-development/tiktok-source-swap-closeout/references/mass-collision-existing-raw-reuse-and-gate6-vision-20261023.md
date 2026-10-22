# Mass Collision Resolution: Existing Raw Reuse, Overwrite Start-Seq, and Gate 6 Local Vision Verification (2026-10-23)

## 1. Problem Statement & Farm Scale Collision
In Taadaa TikTok Farm (Kibe cluster M1–M80, Tik1–Tik8), historical drift and slot formula mapping ($F_{vid} = M \times 8$) caused 9 pairs of channels to collide:
- A channel's render folder `D:/TIKTOK-videonuoinick/<F_vid>/` contained videos rendered from old raw folder `F_vid` (e.g. from an earlier batch).
- However, another live account on the farm owned `Video Goc = F_vid` as its authoritative source.
- Result: Two different accounts on the farm were posting identical frame-by-frame videos, causing the later account to get suppressed (0–110 views).

## 2. Decision Matrix: Fewer-Posted Swap Priority
When two accounts collide on source content:
- Compare `Video Đã Đăng` (posted count) from `snapshots` or the authoritative `Tik<N>.xlsx` workbook.
- The account with **fewer posted videos MUST swap** to eliminate the duplicate footprint.
- The account with **more posted videos KEEPS its source** to preserve its audience retention and established algorithm distribution.

## 3. Existing Raw Reuse Invariant (Zero-Download Acceleration)
Audit the configured raw folder `D:/video goc/<F_src>` of the losing account before attempting any new YouTube/TikTok crawl:
1. In 6 out of 8 collision cases (`F_raw` = `545`, `569`, `514`, `441`, `568`, `579`), the raw folder **already contained 56 to 65 clean, unique videos** and a valid `avatar.jpg` (>30KB).
2. **Strict Rule**: If valid videos $\ge 40$ already exist in `D:/video goc/<F_src>`, DO NOT re-download. Immediately leverage the existing raw pool.

## 4. Preservation of Posting Cursor via Overwrite Start-Seq
When rendering from `D:/video goc/<F_src>` into `D:/TIKTOK-videonuoinick/<F_vid>`:
- The loser account has already posted $N$ videos ($1.mp4$ to $N.mp4$).
- Set `start_seq = N + 1`.
- Use `random_batch_render.py` with `--overwrite`:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py \
    --input-dir "D:/video goc/<F_src>" \
    --output-dir "D:/TIKTOK-videonuoinick/<F_vid>" \
    --preset "D:/Taadaa/Tiktok-video/presets/preset_owner.json" \
    --randomize \
    --overwrite \
    --slot <slot_idx_0> \
    --machine-id <machine_idx_0> \
    --start-seq <N+1> \
    --run-id "kibe-m<M>-slot<Tik>-f<F_src>"
  ```
- **How `--overwrite` with `--start-seq` works**:
  - `make_tasks` enumerates input videos starting from `seq = start_seq` (i.e. $(N+1).mp4, (N+2).mp4, \dots$).
  - Files $1.mp4$ to $N.mp4$ are **never in the task list** and remain **100% untouched** (preserving historical uploaded videos).
  - Existing stale files $(N+1).mp4$ onwards in `F_render` are overwritten with the new derivative videos from `F_src`.

## 5. Avatar Synchronization
Synchronize `avatar.jpg` before or immediately after rendering:
```bash
cp "D:/video goc/<F_src>/avatar.jpg" "D:/TIKTOK-videonuoinick/<F_vid>/avatar.jpg"
```
Verify size > 1,000 bytes. Do not run `_make_avatar.py` if a clean avatar already exists.

## 6. Gate 6 Visual Verification via Local File Browser Navigation
Under Coordinator Guard rules where ffmpeg commands or arbitrary subprocess scripts may be denied:
1. Extract sample frame using pipeline or locate `sample_new_render_*.jpg`.
2. Load local image directly into Chromium via `browser_navigate("file:///C:/Users/Kibe/<sample>.jpg")`.
3. Call `browser_vision(question="...")` to visually inspect the rendered frame.
4. Verify:
   - Aspect ratio: 9:16 vertical (1080x1920).
   - Content: Clean scene matching the expected niche (no old creator re-leak).
   - Subtitles: Sharp, legible, centered Vietnamese captions with highlight.
   - Defects: No black borders, no distortion, no overlay glitches.
5. Only attach `MEDIA:<path>` to the user message after confirming visual verification.

## 7. Metadata and State Reconciliation
After rendering completes with exit code 0:
- Update `Tik<Slot>.xlsx` row for `machine`:
  - `Kiểm Tra Dữ Liệu = 'OK'`
  - `Render Status = 'OK'`
  - `Avatar = 'OK'`
  - Keep `Video Đã Đăng` unchanged.
- Update `avatar_replace_queue` in `D:/Taadaa/data/tiktok_tracker.db`:
  - `UPDATE avatar_replace_queue SET video_goc = '<F_src>', status = 'DONE' WHERE folder_video = '<F_vid>' AND host_id = 'kibe'`
- Update `global-ledger/Kibe.jsonl` if a new channel claim was acquired.
