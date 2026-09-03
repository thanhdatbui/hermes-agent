# Shared-output folder isolation and reconciliation

## Trigger

Use when multiple downloader state DBs, manifests, or batch runners write to one output root and a folder contains both numeric filenames and title-based filenames.

## Evidence-first inventory

For each candidate folder:

1. Count real `.mp4` files, excluding `.part.mp4`.
2. Split filenames into numeric (`N.mp4`) and title-based (`[title] [youtube_id].mp4`).
3. Query every state DB that may use the output root for `folders` and `videos` rows matching the folder number or `output_path`.
4. Compare `(source_channel, platform, niche, status, output_path)` across DBs.
5. Treat a collision as confirmed only when two sources/DBs point to the same output folder; do not infer from filename style alone.

## Safe move contract

- Never delete or overwrite source files.
- Choose the next unused folder number across the shared output root and all relevant DBs.
- Move only files belonging to one source, using DB `output_path` and video IDs as the allowlist.
- Preserve `avatar.jpg` and any source manifest only when their ownership is proven.
- Verify source and destination file counts, non-zero sizes, and no duplicate destination names before updating state.
- Update every authoritative DB that owns moved rows; keep unrelated DBs unchanged.
- Mark the new folder complete only after `video_count` and on-disk count meet the configured target.

## Downloader launch gate

Before starting a batch:

- Ensure no other downloader process targets the same output root/state space.
- Reserve a folder only if the folder is absent or explicitly owned by the same source and resumable.
- If a folder already contains files from another source, allocate a new folder; never reuse the number merely because a different DB says it is pending.
- Run one process first and verify real MP4 files plus DB status/count. Scale only after this check.

## Reporting

Report separately: code fix, collision inventory, move result, and live downloader result. Do not call a canary in another folder proof for the user's target folder.
