# Avatar Upload Farm Fix — 2026-08-15 (Tik2, 55 machines)

Toàn bộ chuỗi fix đã commit `e329cc7` (6 files, 314 insertions). Kết quả: 54/56 máy `AVATAR_SMOKE_SUCCESS` verified; còn 2 máy (27, 32) lỗi uiautomator thiết bị cố hữu.

## Root cause 1: Photo picker mở TRƯỚC khi push/index → AVATAR_SAVE_SELECTOR_MISSING (COMPAT-AVATAR-011)

- Triệu chứng: picker hiện "Gần đây: 0" hoặc tap tile không đăng ký selection → `AVATAR_PICKER_NO_MATCH` / `AVATAR_SAVE_SELECTOR_MISSING`.
- Gốc: code mở picker trước, rồi mới push+index MediaStore → grid snapshot cũ → ảnh mới không có trong grid → tap trượt.
- Fix: **push + index MediaStore TRƯỚC, mở picker SAU**. Bằng chứng: cùng 1 file avatar mới (MD5 `a7060db…`), 2 lần chạy pre-fix fail, 1 lần post-fix SUCCESS (máy 4).
- Evidence dirs: `run_ad061603104ee741e2_20260814_213547` (picker "Gần đây: 0"), `run_988633474f4b514436_20260814_212927` (save surface OK).

## Root cause 2: AVATAR_SOURCE_MISSING — folder mapping 2 root (máy 40-74)

- `resolve_avatar_path(avatar_source_root, folder_video)` dùng cột **Folder Video** từ workbook (state_machine.py:5457), KHÔNG phải cột `video gốc`.
- Tik2 máy 40-74 có Folder Video 314..586 — chỉ tồn tại trong `D:\TIKTOK-videonuoinick\<folder>` (45 mp4/folder); `D:\video goc` chỉ có 1..297.
- Fix: đảm bảo `avatar.jpg` tồn tại ở **CẢ 2 root**: `D:\video goc\<Folder Video>\avatar.jpg` (avatar_source_root — code resolve ở đây) VÀ `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`. Copy từ root có video sang root còn lại.
- Pitfall: `_make_avatar.py` có `SOURCE_ROOT = D:\video goc` cứng → folder chỉ có ở TIKTOK-videonuoinick báo `FOLDER MISSING`. Với root khác, gọi `make_representative_avatar` trực tiếp hoặc copy file sau khi generate.

## Root cause 3: Rule 3-bước ladder dừng sau B1 tại CONNECT_DEVICE

- Triệu chứng: `DEVICE_STARTUP_FAILED: non_xml_ui_dump` — log chỉ có "B1 ATX-kill", không có B2/B3, rồi MANUAL_REVIEW.
- Gốc: `_handle_connect_device` chạy B1 rồi `return False` ngay (state_machine.py ~2207), không bao giờ tới `_execute_with_ui_retry` (nơi gọi `_maybe_soft_reboot_recovery`).
- Fix: startup fail → B1 ATX-kill → **B2** (re-run `prepare_android_for_automation`, nếu OK thì tạo adapter+media_manager và return True) → **B3** (`_maybe_soft_reboot_recovery` bounded) trước khi MANUAL_REVIEW. Cứu 5/9 máy recovery (72, 40, 36, 58, 46).
- Lưu ý: `_maybe_soft_reboot_recovery` cần `device_transport` (set ở run_post.py:1374 trước execute) + screenshot artifact; máy uiautomator chết có thể vẫn skip B3 (`pre-recovery artifact unavailable`).

## Root cause 4: Máy kẹt Recent apps sau B3 reboot → AVATAR_UPLOAD_MENU_MISSING (COMPAT-RECENTS-ESCAPE-001)

- Triệu chứng: sau B3, máy nằm ở màn hình Recent apps (App Switcher, có nút "ĐÓNG TẤT CẢ"); workflow không thấy menu "Tải ảnh lên" → `AVATAR_UPLOAD_MENU_MISSING`.
- Gốc: `close_all_recent_apps` mở Recent (keyevent 187) rồi **cần uiautomator dump** để tìm nút clear-all; uiautomator chết (`non_xml_ui_dump`) → fail → app không launch được.
- Workaround thủ công đã chứng minh (máy 69/71): **bấm HOME (keyevent 3) thoát Recent** (không cần dump) → vào app.
- Encode: trong vòng lặp relaunch của OPEN_TIKTOK, probe `_read_focused_activity`; nếu focused activity chứa "recents"/"recent" → `input keyevent 3` + sleep 1s trước `prepare_app_for_automation`. Máy 69 + 71 pass sau fix này.

## Verifier: avatar-only success bị đếm LỖI sai

- `run_tiktok_upload_batch.ps1:486-492` chỉ verified khi `status=="SUCCESS" AND post_verified==true`. Avatar-only report có `AVATAR_SMOKE_SUCCESS` + `avatar_status=FORCED_REPLACED_VERIFIED` → mọi máy thành công bị "worker exit=0 nhưng thiếu report/verifier proof; chuyển MANUAL_REVIEW" → LỖI.
- Fix: thêm nhánh `elseif ($AvatarOnly) { $report.status -eq "AVATAR_SMOKE_SUCCESS" -and $report.avatar_status -eq "FORCED_REPLACED_VERIFIED" }`.

## Avatar generation workflow (55 máy + 335 folder)

- Spec user: người → không có người thì động vật (YOLO) → fallback frame sáng. `make_representative_avatar(subject_type)` (pipeline_common.py:329-468) đã implement: person Haar faces / animal YOLO classes (bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe) / gom cụm theo binary hash → crop vuông 512×512 JPEG q92.
- Niche → subject_type: `{yeuthucung, xemeo, chocanh, thucung}` → animal, còn lại → person (source_pool_builder.py `subject_type_for_niche`).
- `download_by_niche.py` thêm `make_avatar_for_folder`: 1) avatar kênh thật (authoritative) → 2) frame người/động vật theo niche → 3) frame sáng 512×512. Trước đây chỉ avatar kênh → thiếu là INSUFFICIENT_POOL.
- Generation song song: 4 worker × ~69 folder (chia `parts[idx::4]`), ~25s/folder (ffmpeg+cv2), 275 folder ≈ 25 phút. Folder tv_only (chỉ ở TIKTOK-videonuoinick) cần mode riêng trỏ đúng root.
- Verify ảnh bằng vision trước upload: vài file generated chỉ 4-8KB là nghi ngờ nội dung lỗi.

## Workflow rules được củng cố

- Mọi workaround thủ công thành công PHẢI được encode vào canonical script ngay (user: "có fix = debug ảnh thật hay tap đúng UI gì cũng phải handle lại chứ", "m đã lưu handle cách fix qua script chưa").
- CẤM 2 batch chạy song song (tranh lock → skip loạn). Kiểm tra process batch cũ trước khi launch batch mới.
- Máy 38: CẤM đụng (tiến trình khác).
- Trước khi kết luận "folder thiếu avatar": check CẢ 2 root (`D:\video goc` + `D:\TIKTOK-videonuoinick`).
- Tạo avatar theo đúng cột Folder Video từ workbook, không theo `video gốc`.
