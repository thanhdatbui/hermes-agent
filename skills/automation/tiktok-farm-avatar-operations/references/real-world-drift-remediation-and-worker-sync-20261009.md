# Real-World Drift Remediation & Background Worker Sync (2026-10-09)

## 1. Overview
Remediating an account that has experienced extreme topic drift:
- Earlier: Female Gen Z vlog / agency content (high engagement, 765 views).
- Recent: Dashcam traffic accidents (stuck at 48 views).
- Avatar: Distorted yellow circle reading "hôi" due to automatic banner cropping.

## 2. Key Insights
- **Advisory:** Never keep the drifted accidental niche. Algorithm swipe-away penalizes audience mismatch immediately.
- **Database Boundary:** Ground-truth `state.db` is located at `C:\CodexRuntime\tiktok-video\state.db`, not empty 0-byte placeholders on drive D:. Folders updated in the Sept 11 normalization (480..640) had their metadata overwritten.
- **Scraping Bypass:** Use `sec_uid` extracted via regex from profile HTML to scrape TikTok playlists without tripping secondary user ID errors in `yt-dlp`.
- **Render Worker Lock Prevention:** Synchronize `video gốc = Folder Video` in `Tik<N>.xlsx` so the background worker (`run_kibe_render_worker.py`) renders the new source rather than locking files from an old raw directory (`WinError 32`).
- **Device Lock Handoff:** Wait for active device locks (such as 2FA) to clear before triggering `run_tiktok_upload_avatar.ps1`, then verify with Vision API and return `MEDIA:`.
