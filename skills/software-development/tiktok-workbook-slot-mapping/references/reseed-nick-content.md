# Reseed nick content — evidence checklist

Use this reference when replacing a nick's entire content pool because the old source/channel is wrong.

## Required evidence before destructive action

- Exact account ID from the current authoritative workbook; similar-looking IDs are not interchangeable.
- Machine, slot/TikN, source (`video gốc`) folder, and render (`Folder Video`) folder from that same mapping.
- Ownership check: source/render folders belong to the target account and are not being used by another active process.
- Active-process check for downloader, renderer, and upload workflow.
- Spare source candidate: at least 45 valid MP4s, not already rendered or assigned to an active account. Record its number and count before moving it.

## Fixed execution order

1. Remove the target account's old source and render content within the authorized scope.
2. CUT the spare source into the target source folder; never copy and leave a duplicate.
3. Verify the spare source is empty of MP4/title-based leftovers.
4. Run the Kibe/local random renderer to the target render folder with the correct paths, randomization, and one FFmpeg worker.
5. Validate numbered `1.mp4..N.mp4` outputs with ffprobe.
6. Only after target rendering succeeds, run the downloader to refill the spare source folder. Keep `--min-videos >= 30`, existing state DB, source pool, global ledger, and output root.
7. Reconcile target and spare counts, paths, avatar, DB, and workbook mapping.

## Known traps

- `run_tik1_random_render.ps1` may be an Admin runner pointing at `D:\video goc may 2` and `D:\TIKTOK-videonuoinick-admin`; do not use it for Kibe data without verifying its paths.
- A source folder number is not proof of ownership or render history. Use manifests/workbook/artifacts.
- Runtime logs are historical evidence only; they cannot override the current exact account mapping.
- If interrupted, resume the current phase; do not repeat deletion or create a second downloader/renderer.
