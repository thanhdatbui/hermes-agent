# Tik3 render + avatar — 2026-08-16 session detail

## Tik3 render (tik3_multi_batch.py — FIXED, usable)

Previously "wrong entrypoint" (needed `sttvideo` column). Fixed in-repo: `find_headers`
now falls back to the `Folder Video` column for `sttvideo` when missing.

Proven command (resume semantics, worker 1, skips existing):
```
export PYTHONPATH='D:/Taadaa/Tiktok-video/scripts'
D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m tik3_multi_batch \
  --workbook "D:/OneDrive/TaadaaData/kibe/Tik3.xlsx" \
  --start-output <OUTPUT> --start-source <SOURCE> \
  --count 10 --min-videos 45 --parallel 1 \
  --allow-existing-output --resume-complete --execute
```
- `--start-output`/`--start-source`: from the workbook row, e.g. máy 45 → output 355,
  source 205. Source increments +1 per output.
- `--resume-complete` alone FAILS on a partial folder (has mp4 but <45): it only
  considers "complete" at full count, and ensure_output_ok blocks any folder with mp4.
  Must add `--allow-existing-output` → batch_render then skips existing files and
  renders only the missing ones.
- `--overwrite` does NOT get past ensure_output_ok for a partial folder; do NOT use it
  (and never delete output files to "reset" — see SKILL.md pitfalls).
- Workbook is backed up automatically (`Tik3.xlsx.bak_<ts>`) before render.
- Render writes `video gốc = <source>` back into the workbook row when the folder
  completes; `batch_render` also copies avatar.jpg from source→output (`COPY avatar:`).

## Tik3 regression status 2026-08-16
- Folders 1-44 (output 3..347) were already rendered 2026-08-11..14 (máy 44 = 347 had
  only 24/45 — incomplete).
- Rendering resumed from máy 45 (output 355) onward: 355, 363, 371 completed.
- Remaining: 379..635 (batch of 10 each, start-output/start-source stepping +8/+1),
  plus máy 44 folder 347 to finish (21 videos missing).

## Avatar NEW rule (overwrite Tik3 onward)

Old avatars are wrong content → regenerate. Rule: person → animal → bright frame
(`make_representative_avatar`, called via `_make_avatar.py` for source folders).

### Avatar scripts (D:\CodexRuntime\tiktok-video\)
1. `avatar-tik3-all-20260816.py` — overwrites avatar for ALL `D:\video goc` folders ≥161
   (skips 1..160 used by Tik1/Tik2). Uses `_make_avatar.py <folder_number>`; if a folder
   has no video in video goc, falls back to generating from the TV folder.
2. `avatar-tv-fallback-20260816.py` — generates avatar direct from
   `D:\TIKTOK-videonuoinick\<folder>` via make_representative_avatar with subject_type
   "person" (used for output folders 305-586 whose videos live only in TV).
   Data file: `avatar-worker-folds.json` (`{"parts": [...], "tv_only": []}`).

### Key facts
- `D:\video goc`: 333 folders (1-586); 297 with video, 36 WITHOUT (305,306,314,322,... =
  Tik3 OUTPUT folders only — their videos are in TV).
- `D:\TIKTOK-videonuoinick`: 208+ folders, ALL with video, includes everything.
- Workbook media source root = `D:\TIKTOK-videonuoinick` (avatar_source_root falls back
  to media_source_root) → workflow reads avatars from the TV/output folder.
- Verified: hashtags in Tik3.xlsx TaiKhoan sheet match the "Hashtag theo Folder" sheet
  per source folder (80/80), NOT copied from Tik1/Tik2 (Tik1/2/3 use distinct niches per
  machine).

## Lock rule (all repos, 2026-08-16)
Lock/unlock ONLY on explicit user command; auto-lock CẤM; auto-unlock only on SUCCESS
(fail/manual/abnormal exit keeps lock in handoff state, blocking re-run). Enforced via
`acquire_device_lock(user_authorized=False)` default no-op in automation-core; all
D:\Taadaa consumer repos either import core or were patched (Tiktok_Reg device_lock.py
default True→False commit 5891817; tiktok-add-bao-mat-f2a +user_authorized=False ×4
commit 6fa3d13). gan-proxy lock: CẤM đụng.

## Avatar rule ƯU TIÊN CAO NHẤT (user đổi 16/08 chiều tối — SỬA CẢ 2 SCRIPT)
- User: "đưa rule người→động vật→frame sáng lên ưu tiên CAO NHẤT" → **BỎ hoàn toàn avatar
  kênh thật (channel_avatar_url) khỏi bước 1** của `make_avatar_for_folder` (download_by_niche.py).
  Thứ tự: 1) người (face via make_representative_avatar, person) → 2) động vật (subject_type
  theo niche: yeuthucung/xemeo/chocanh/thucung → animal; cần yolov8n.pt auto-download ~6.5MB
  ở repo root) → 3) frame sáng crop 512×512. Commit `662ff58` (download_by_niche) + `0b2fc7d`
  (_make_avatar.py: subject_type `person`→`auto` + subject_model=yolov8n.pt path).
- **"Những cái đã sửa r thì đừng đụng tới nữa" (user)** — avatar Tik3 161+ đã tạo theo rule cũ
  (person→fallback frame) GIỮ NGUYÊN; rule mới chỉ áp cho lần chạy SAU (download folder mới).
  KHÔNG chạy lại _make_avatar trên folder đã có avatar để "đồng bộ rule" — bị user phạt.
- Canary test _make_avatar trên folder đã có avatar cũng vi phạm rule trên — nếu test thì
  chọn folder CHƯA có avatar, hoặc backup+restore avatar cũ ngay sau test.

## Download video gốc 298-480 — session detail (tối 16/08)
- Mục tiêu user: `D:\video goc` phải đủ **480 folder có video** (hiện 297 có video, thiếu
  183: 298-480). "folder gốc chưa đủ 480 thì phải tải thêm" — dùng download_by_niche
  (tích hợp sẵn tạo avatar mới — không cần bước avatar riêng).
- **Lỗi điển hình + nguyên nhân (3 lần fail folder 299 dongluc):**
  1. `HTTP Error 403: Forbidden` rải rác khi tải YouTube = **rate-limit/anti-bot tạm thời**,
     retry folder lại là qua (folder 298 khoahoc pass 65/65 ở lần chạy thứ 2). KHÔNG kết luận
     "YouTube hỏng".
  2. `INSUFFICIENT_POOL platform=instagram` — IG 403 chặn API, yt-dlp 2026.07.04 mới nhất
     không có fix. Dẹp IG: sửa PLATFORMS + PLATFORM_TARGET (50/50 vẫn chọn TikTok dù chỉ
     5 source → fail).
  3. `INSUFFICIENT_POOL platform=tiktok best_candidates=4` — nguồn TikTok khan hiếm
     (auto-discover ra ~4-5 handle/80 niche); PLATFORM_TARGET phải nghiêng YouTube.
- **CHỐT CUỐI PLATFORMS (commit `241424f`):** `PLATFORMS=("youtube",)`,
  `PLATFORM_TARGET={"youtube": 1.0}` — TikTok dẹp hẳn vì kể cả target 0.15, `choose_platform`
  (chọn theo ratio count/target) vẫn chọn TikTok trước (ratio 0) → mọi folder gán TikTok fail.
  Kèm flag mới `--continue-on-insufficient` (BẮT BUỘC cho batch dài): mặc định
  INSUFFICIENT_POOL → `return 2` dừng cả batch; flag này skip folder thiếu nguồn chạy tiếp
  (user: "kênh nào đủ điều kiện thì down luôn").
- **Qualify gate bắt buộc:** `--auto-discover` thiếu `--qualify-videos` → 0/176 sources có
  `qualified_video_count`. Lệnh qualify PHẢI có `--min-sources-per-platform 0` (không có →
  exit 2 `INSUFFICIENT_SOURCE_POOL: thieu platform ['instagram']` dù đã dẹp IG). Kết quả
  verify: 70/70 qualified ≥45 video (YT 67 + TT 3) → download chỉ nhận `sources.qualified.json`.
- **Đọc `sources.qualified.json`:** output dạng DICT không phải list —
  `rows = data if isinstance(data, list) else data.get("sources", [])`; đọc sai format →
  `AttributeError: 'str' object has no attribute 'get'`.
- **Qualify noise không phải lỗi:** `[youtube:tab] ... does not have a shorts tab`,
  `This video is not available`, `[TikTok] Unexpected response` = probe thử tab/video hỏng,
  bỏ qua tự nhiên; rate-limit YouTube gây "not available" hàng loạt = chặn tạm, chạy nền
  kiên nhẫn.\n- **Sau khi sửa code loop:** process giữ module cũ — phải KILL + restart
  qualify/download loop, không patch xong bỏ chạy.
- **PITFALL reset folder fail:** `UPDATE folders SET status='pending'` KHÔNG đủ — folder_row
  đọc lại `platform` cũ ('instagram') → fail lại. Reset cả:
  `UPDATE folders SET status='pending', platform='pending', source_channel=NULL, video_count=0
  WHERE folder_num=<N>`.
- **Discovery thiếu qualify:** `source_pool_builder --auto-discover` không flag
  `--qualify-videos` → mọi source `qualified_video_count=None` → kênh 4-video lọt pool →
  INSUFFICIENT_POOL. Phải chạy qualify (xem SKILL.md). Test nhanh eligible source:
  `load_sources(Path(...))`; `Source` constructor cần path khác, không truyền dict.
- **youtube_profile Unicode:** regex cũ `@[A-Za-z0-9._-]+` fail handle tiếng Việt
  (`@KhámPháBếpViệt`) → `@[\w.-]+` (source_pool_builder.py đã commit).
- **yt-dlp TikTok extractor "marked as broken"** (bản 2026.07.04) — không search/tải TikTok
  qua yt-dlp; TikTok search URL (`tiktok.com/search`) Unsupported URL. Nguồn TikTok chỉ từ
  URL channel đã biết.
- **Cookies:** Chrome/Edge `--cookies-from-browser` fail (App-Bound/DPAPI — issue #7271);
  Firefox đọc được nhưng cần profile có youtube cookies (profile không login → vô dụng).
- **Pool proxy farm KHÔNG dùng cho download** (phục vụ device TikTok, đụng lock; 403 là
  rate-limit theo IP thời điểm, retry là đủ) — user đồng ý không tăng worker do sợ spam IP.
- **Không tăng worker** dù chậm: discovery <=4, download `--parallel 1`, qualify 4.
- **Chạy song song:** tạo `qualify-loop-20260816.py` / `download-loop-20260816.py`
  (D:\CodexRuntime\tiktok-video\) — copy `sources.partial.json` (checkpoint discovery ghi
  sau mỗi niche) → manifest JSONL (lọc IG + vtv24) → chạy qualify/download → sleep 120s →
  lặp tới khi discovery process chết. Log riêng: `qualify-loop.log` / `download-loop.log`.