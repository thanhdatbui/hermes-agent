# VIDEO_PICK batch fail 24/24 — Profile surface + verifier gaps (2026-08-09)

Batch Tik1 24 máy ít video (`assignment-tik1-lowcount-20260809_215614.json`, máy 1,2,3,8,12,13,17,24,25,26,27,28,29,35,37,39,42,44,45,48,54,70,72,74) — **3 lần chạy đều 24/24 LỖI exit 2**, signature chính `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`, phụ `VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET`, `OPEN_TIKTOK_FAILED`.

## Chuỗi bằng chứng (đừng kết luận sớm — đọc log trước)

1. **Worker restart TỪ ĐẦU, không phải resume màn cũ** (run `run_ce061606c21e153d03_20260809_234548` execution.log):
   - `close_all_apps_start: success` → `[OPEN_TIKTOK] Force-stop + relaunch 1/2` → `force_stop_app: success` → `launch_app: success` → `[WAIT_FEED] Root surface confirmed with indicator: 'đề xuất'` → `Feed/home screen confirmed ✓` (23:46).
   - ⇒ KHÔNG được đổ lỗi "máy kẹt màn soạn từ phiên sáng" khi log chứng minh worker đã force-stop + mở lại sạch. **User-caught 2026-08-09: "chạy lại từ đầu dính lỗi thế sao m nói là do lỗi từ phiên sáng"** — kiểm chứng causal claim bằng log TRƯỚC khi phát biểu.

2. **Sau relaunch TikTok mở ở tab Hồ sơ (Profile), không phải Feed** — ACCOUNT_SWITCHER tap `Hồ sơ` (972,1883) để verify account, ACCOUNT_READY xong **không quay về feed**; MEDIA_PUSH xong `[WAIT_FEED] Root surface confirmed with indicator: 'hồ sơ'` (23:50) — WAIT_FEED **chấp nhận 'hồ sơ' làm root indicator** → VIDEO_PICK chạy trên sai surface → không có nút "+" bottom-nav → fail. Nút create chỉ tồn tại ở Feed.

3. **Coordinate fallback có bug guard lần gọi thứ 2**: `_recover_video_pick_create_entry` chỉ gọi `_recover_video_pick_create_entry_coordinate` khi `video_pick_recovery_attempted=True` (tức lần gọi THỨ 2), nhưng call-site (dòng ~9063) gọi 1 lần rồi `return False` → coordinate **không bao giờ chạy** dù ladder cạn. Fix: delegation coordinate ngay trong cùng lần gọi sau ladder exhaustion + navigate Feed trước (mới có ở bản sau).

4. **`_find_video_pick_create_entry_point` fail trên XML thiếu display-root**: fixture/raw dump chỉ có node create cô lập (`[432,1794][648,1920]`) → `screen_width = max right = 648` → center check `540 > 0.65*648=421` → None → `feed_surface=False` → coordinate từ chối. Fix: ưu tiên `width/height` param (wm size) làm baseline; khi không có display-root (`right > screen_width` với node duy nhất) chấp nhận label+clickable+bottom-band. Test fixture phải có node root `[0,0][1080,1920]` (test 1 pass vì có, test 2/3 fail vì thiếu).

5. **Verifier không nhận màn soạn caption (composer post-edit)**: `_is_video_pick_create_composer_entry_xml` chỉ nhận camera markers (`x7f`/`tv_top_text`/`video_record_new_scene_root`) + ≥2 label tạo/ảnh/văn bản. Live m46 dump: `Thêm mô tả` + `Đăng` + `Hashtag` + `Nhắc đến` — máy ĐÃ chọn xong video, đứng ở màn soạn caption → worker fail-closed oan. Fix: `"thêm mô tả" in folded and any(marker in folded for marker in ("đăng","hashtag","nhắc đến"))` → True. Regression `test_video_pick_create_composer_classifier_accepts_caption_composer_live_m46`.

## Kỹ thuật probe màn thật hàng loạt (dùng khi nghi UI khác log)

- uiautomator dump có thể exit 137 (Killed) TOÀN FARM — screencap vẫn chạy:
  ```python
  subprocess.run([ADB,'-s',serial,'exec-out','screencap','-p'],capture_output=True,timeout=30)  # png bytes
  subprocess.run([ADB,'-s',serial,'shell','uiautomator','dump','/sdcard/n2.xml'],timeout=25)     # rc 137 = chết
  ```
- Phân loại nhanh ảnh bằng pixel ratios (không cần vision): `white=sum(r,g,b>230)/n`, `dark=sum(<40)/n`, `red=(r>200,g<100,b<100)/n`:
  - `white≈0.86` = màn gần trắng (composer/settings/popup trắng)
  - `dark≈0.6-0.98` = màn tối (video tối / splash / screen off)
  - `white≈0.61` = profile grid sáng
- `vision_analyze` **đã hoạt động trở lại** (resolved key) — dùng để xác nhận feed vs profile vs caption composer trên ảnh screencap; khi 401 mới fallback pixel-stats + UI dump.

## Cơ chế chống trùng video (trả lời user, verify trong code)

- `state_machine.py:1927-1941`: `is_video_already_posted(next_video)` → True ⇒ raise `VIDEO_ALREADY_POSTED` fail-closed, KHÔNG đăng trùng. `next_video = workbook["Video Đã Đăng"] + 1`.
- Video push từ sáng mà chưa đăng thành công ⇒ chưa tính vào `Video Đã Đăng` ⇒ chạy lại đăng chính video đó; đăng xong mới +1. Không có path đăng 2 lần cùng video.

## Launch batch đúng (đã verify lần này)

- `-AssignmentManifest` BẮT BUỘC đi kèm `-WorkerId` == `owner_id` trong manifest — thiếu WorkerId → launcher fail ngay (exit 1, log trong file redirect), KHÔNG phải lỗi máy. (Cùng rule §8c cho RecoveryMode; áp cho cả normal batch.)
- `unset PYTHONPATH` trước powershell (không đủ `PYTHONPATH=` inline nếu đã export).
- Dọn lock stale trước mỗi relaunch: máy target có 2 alias (`machine_<N>` + `serial_<serial>`); pid verify bằng `wmic ... /format:list` (không dùng `/format:csv` — comma trong CommandLine làm vỡ cột).

## Kết quả cuối

Full suite: 371 → 374 passed (fix transport.tap + fixture root node + caption composer verifier + test mới). Vẫn chưa verify batch pass hết — nếu chạy tiếp và vẫn fail, xem tiếp signature mới (có thể máy cần về Feed trước VIDEO_PICK bằng navigate semantic, không chỉ coordinate).
