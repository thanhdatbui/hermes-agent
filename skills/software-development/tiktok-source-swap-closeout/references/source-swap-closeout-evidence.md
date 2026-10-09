# Source-swap closeout evidence checklist

Use exact known paths and bounded queries; never use a broad disk scan.

## Target mapping
- Tracker DB: username → host/machine/slot.
- Exact workbook row: machine, `Folder Video` (render), `video gốc` (raw), niche, and `Video Đã Đăng`.
- `start_seq = Video Đã Đăng + 1`; preserve the posted count.

## Dedup proof
- Shared ledger: list records for the candidate source and target raw folder.
- Separate `source_claimed` from `downloaded` records.
- Compare recorded video IDs across candidate folders; a source claim or a peer row with zero posted clips is not proof of a live duplicate.
- Confirm the replacement source has enough duration-valid videos before cleanup.

## Runtime proof
- Long job launched with completion notification and exact log path.
- On wakeup, read the log/artifacts; do not infer success from PID or exit code.
- Verify raw count, render output beginning at `start_seq`, workbook/database/claim updates, and a real frame or UI screenshot. Send `MEDIA:<absolute path>` before teardown.
- Count reconciliation check:
  - Verify `len(raw_mp4) == len(render_mp4) == db_video_count >= min_target`.
  - Distinguish sequence range (e.g. `10.mp4` to `29.mp4`) from total folder/clip counts (`29 - 10 + 1 = 20` clips in 1 folder).
  - Inspect raw download directory for audio-only leftovers (`.m4a`, `.mp3`) and ensure no download index collision (`WinError 183`) truncated the batch.

## Reporting states
- `RUNNING`: process still active; report the log path only.
- `DONE`: all runtime and visual evidence is present.
- `BLOCKED`: include the actual error and the last verified artifact.

## Niche pivot & view slump investigation (O(1) diagnosis checklist)
When diagnosing an account that suddenly dropped views after an automated migration or swap:
1. **Locate account coordinate**:
   `sqlite3 D:/Taadaa/data/tiktok_tracker.db "SELECT may, tik FROM account_mapping WHERE username = '...'"`
2. **Inspect current vs historical workbook**:
   - Current: `D:/OneDrive/TaadaaData/<cluster>/Tik<Slot>.xlsx` (row for machine).
   - Historical: `Tik<Slot>.xlsx.bak_audit_94_review` or `.bak_before_...` in the same directory.
   - Compare `Keyword Video`, `Hashtag Pool`, `video gốc` to determine original niche before migration.
3. **Verify original content in state DB**:
   `sqlite3 C:/CodexRuntime/tiktok-video/state.db "SELECT video_id, uploader, output_path FROM videos WHERE folder = <video_goc> LIMIT 5"`
4. **Inspect snapshots progression**:
   `sqlite3 D:/Taadaa/data/tiktok_tracker.db "SELECT timestamp, video, heart, follower FROM snapshots WHERE username = '...' ORDER BY timestamp ASC"`
   Compare timestamps against the video count increase to see when view growth stalled.
5. **Hashtag sanity check**:
   Ensure `Hashtag Pool` does not contain artificial suffixes (e.g. `#<slug>vietnam`, `#<slug>moingay`). Use natural high-volume search tags only.

## Revert channel discovery from global ledger & oEmbed (Zero-ask recovery)
When an account needs to be reverted to its previous high-performing channel:
1. **Never ask the user for the original channel URL**: The farm's crawl history already tracks all previously claimed channels.
2. **Query the shared ledger**:
   Filter `D:/OneDrive/SharedData/tiktok-video/global-ledger/*.jsonl` for `"folder":<raw_or_render_folder>` to discover all candidate `source_url`s.
3. **Match historical video titles**:
   Cross-reference visible video titles on the profile screenshot (or `state.db`) against candidate channel videos using `yt-dlp --flat-playlist` or TikTok oEmbed (`https://www.tiktok.com/oembed?url=<url>`) to pin down the exact channel.
4. **Bypass TikTok Secondary User ID Extraction**:
   If yt-dlp throws `Unable to extract secondary user ID`, fetch `sec_uid` (`MS4wLjABAAAA...`) from oEmbed metadata or video URL, and pass `https://www.tiktok.com/@<sec_uid>` directly into `--channel`.
5. **Salvage leftover raw videos to Curated Pool**:
   Before staging/cleaning the target folder, preserve any downloaded videos from other niches by moving them into `D:/video goc/curated_pool` with a distinct prefix (`pool<folder>_*`) so they remain available for aggregate/curated channels.
