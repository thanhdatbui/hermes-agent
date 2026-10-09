# Drift Reversion, Ground Truth DB, and Background Render Worker Coordination (2026-10-09)

## 1. Context & Operator Trigger
Operator notices a severe topic drift on an active account:
- Earlier videos: High-performing niche (e.g. Gen Z daily vlog / female creator reaching 700+ views and organic followers).
- Latest videos: Mismatched, jarring niche (e.g. dashcam traffic accidents stuck at 48 views).
- Avatar: Distorted, cut-off text from accident warning banners (e.g. banner word "thôi" cropped into "hôi").
- Questions asked by operator:
  * *"Chứ kênh cũ tải có lưu ở file db hay gì đó chứ???"* (Asking if the database stores crawl history)
  * *"Giữ nguyên hay đổi lại?"* (Asking whether to keep the traffic niche or revert)

## 2. Operator Advisory & Decision Matrix
1. **Never Recommend Keeping the Drifted Accidental Niche:**
   - **Audience Graph Slump:** The account's initial followers and seed audience engaged with lifestyle/vlog. TikTok's recommendation engine tests new uploads against this existing audience first. An immediate mismatch produces extreme swipe-away rates, suffocating the video at tier 1 distribution (48 views).
   - **Policy & Community Guideline Hazards:** Dashcam crash footage and accident scenes carry elevated risk of violence/shocking content strikes, leading to permanent shadowbans.
2. **Database Traceability Boundary (Pre-Sept 11 vs Post-Sept 11):**
   - The authoritative metadata DB is `C:\CodexRuntime\tiktok-video\state.db` (34 MB), NOT the empty 0-byte placeholders under `D:\` or OneDrive.
   - During the Sept 11, 2026 normalization, folders 480..640 were overwritten in `state.db` with newly assigned bulk channels (e.g. folder 496 was overwritten with `@Cameragiaothong`).
   - If the original creator was used prior to Sept 11, explain the database boundary clearly to the operator rather than performing expensive recursive disk scans.

## 3. Autonomous Execution & Pipeline Synchronization
1. **Zero-Friction Channel Selection:**
   - If the operator does not remember the exact original account, select an exclusive, unshared creator with identical demographics, style, and setting from the 12 Hot Niches (e.g. `@_yennhi204_` - student life, daily vlog).
   - Verify zero collisions across all 16 farm workbooks and `global-ledger/*.jsonl`.
2. **TikTok Playlist Scraping via `sec_uid`:**
   - Scrape the profile HTML for `secUid` (`MS4wLjABAAAA...`) and pass the playlist URL `https://www.tiktok.com/@<sec_uid>` to `yt-dlp` to bypass the `Unable to extract secondary user ID` blocker.
3. **Preventing Background Render Worker Collisions (`WinError 32`):**
   - `run_kibe_render_worker.py` monitors `Tik<N>.xlsx`. If `video gốc != Folder Video` (e.g. 622 vs 496), the worker will detect missing render files and continuously render from the obsolete `video gốc`, locking files (`WinError 32`).
   - **Immediate Fix:** In `Tik<N>.xlsx`, set `video gốc = Folder Video`, set `Keyword Video` to the new niche, preserve `Video Đã Đăng` (e.g. 8), and append the transaction to `global-ledger/Kibe.jsonl`.
   - The background render worker will automatically transition to rendering the new source files sequentially without manual intervention.
4. **Handoff from Device Lock to Live Avatar Replacement:**
   - If the physical device is occupied by an active automation lock (e.g. 2FA `phase-b-live`), set `avatar_replace_queue` to `PENDING` and report `SKIPPED_LOCKED`.
   - As soon as the device unlocks and render reaches 45/45, launch the canonical avatar-only runner (`run_tiktok_upload_avatar.ps1 -ForceAvatarMachineList <M>`), verify the `avatar-uploaded-confirmed.png` screenshot using Vision API, and deliver `MEDIA:<path>` to the operator.
