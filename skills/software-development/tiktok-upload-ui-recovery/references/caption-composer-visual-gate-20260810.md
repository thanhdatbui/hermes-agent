# Caption composer visual gate khi uiautomator dump chết (2026-08-10)

Session: batch 24 máy fail nhiều vòng (23:40 → 00:45 → 04:04), fix đêm dài
trên máy 24/13/35/74. Bài học lớn nhất: **worker và máy thật cách nhau 1
lớp XML — khi dump UI chết (uiautomator exit 136/137 farm-wide), mọi
classifier semantic trả false negative và worker fail oan dù UI thật đã tới
bước cuối**. User bực ("đéo up đc cả video") vì 4 batch liên tiếp 0 success
dù ảnh anh ấy chụp cho thấy **máy nào cũng tới được màn soạn caption**.

## Chuỗi signature & root cause

| Signature | Root cause thật | Fix |
|---|---|---|
| `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED: Coordinate create-entry fallback: Feed was not verified before tap` | Machine đứng **profile detail** (own-video player, không navbar) hoặc **màn hình TẮT** (screen timeout ~90s MEDIA_PUSH không tương tác → `dark=0.976`) | `_is_video_pick_profile_detail_surface` + Back→Trang chủ; `_ensure_screen_on` (keyevent 224) |
| `Editor Next tapped but caption composer did not open` → attempt 2 `Feed was not verified` | **FALSE NEGATIVE**: caption composer ĐÃ MỞ ("Thêm mô tả..." + nút Đăng) nhưng XML rỗng → `_is_final_composer_surface` trả False | `_visual_caption_composer_likely` pixel gate |
| `CAPTION_FILL: Caption field not found via selectors` ×3 | XML rỗng → `_find_caption_field` None | coordinate tap + `_type_caption_coordinate` |

## Bằng chứng pixel (m24 live, run 04:47)

- `Visual caption-composer gate white=0.865 red=0.030 tr=0.000 br=0.431 matched=True`
  — **br (bottom-right crop) = 0.431** bắt được nút Đăng; tr (top-right) = 0.000
  vì build 46 đặt nút Đăng **dưới-cùng BÊN PHẢI** (Nháp trái + Đăng đỏ cam phải).
- m13 run 04:07: `white=0.705, dark=0.000, red=0.291` = màn soạn caption sáng
  toàn phần. Visual create-button gate cũ reject vì yêu cầu `dark>=0.005`
  (vùng bottom crop) — màn sáng → dark=0 → reject oan.
- m24 run 04:25: `white=0.865 red=0.030` — nút Đăng build 46 **HỒNG SÁNG và NHỎ**
  (250,60,110), toàn-màn red chỉ 0.030 < ngưỡng 0.08 cũ → đổi red/pink detector
  `r>180, g<170, b<200` + crop top-right/bottom-right riêng.

## Fix đã commit (Tiktok-video, main)

- `908462f` — `_visual_caption_composer_likely`: white≥0.40 + red toàn màn ≥0.08.
- `dbd3f07` — mở rộng detector pink + top-right crop (70-100%w, 4-22%h).
- `eee3ea0` — bottom-right crop (70-100%w, 85-99%h) — nút Đăng build 46 nằm dưới-cùng.
- `6381897` — CAPTION_FILL coordinate tap caption field (0.28w, 0.13h) khi XML
  chết + visual composer confirmed; bỏ `_clear_caption_input` (XML-dependent) —
  field trống vì composer vừa mở với video mới chọn.
- `5a96177` — `_type_caption_coordinate`: tap → `input text` từng chunk
  (CAPTION_TYPING_CHUNK_SIZE=400, escape `#`/space, verify ack) — skip
  clear + skip chunk-XML verify vì dump chết.

## Regression tests (tests/test_tiktok_workflow.py)

- `test_video_pick_final_composer_visual_fallback_when_xml_empty`
- `test_video_pick_final_composer_visual_rejects_dark_feed`
- `test_video_pick_final_composer_visual_accepts_small_pink_post_button`
- `test_video_pick_final_composer_visual_accepts_bottom_right_post_button`
- `test_caption_fill_coordinate_fallback_when_xml_dead_and_visual_composer` (assert tap (302,249) = 0.28×1080, 0.13×1920)
- `test_caption_fill_type_coordinate_when_xml_dead` (input text chunks via adb)

Fixture pitfall: visual gate gọi `transport.screenshot(run_dir/...)` — test
phải truyền `reporter=SimpleNamespace(run_dir=tmp_path)` (run_dir=None →
capture fail → trả False sớm). Nút đỏ test phải đủ lớn (≈10% diện tích ảnh)
để qua ngưỡng red.

## Quy trình vận hành đêm đó (lặp lại mỗi vòng fail)

1. Đọc summary.csv batch (`encoding=utf-8-sig`) → nhóm máy theo signature.
2. ATX kill toàn farm target: `uiautomator quit; pkill -f atx-agent; pkill -f com.github.uiautomator` (24 máy ~2 phút). Dump hồi phục 137 → OK.
3. Dọn lock máy fail: archive `machine_<N>.lock.json` + `serial_<hex>.lock.json`
   vào backup có evidence (pid chết verify bằng wmic `/format:list`).
4. Xóa entry fingerprint `reserved` fresh (<1800s) — **XÓA FILE, KHÔNG set
   status='released'** (released không phải status hợp lệ → worker vẫn fail
   "unresolved ledger status=released"; mắc thật 2026-08-10). An toàn chỉ khi
   mọi run máy đó `post_submission_state=None` (video chưa từng đăng).
5. Launch: worker-id PHẢI = owner_id trong manifest (`-WorkerId
   hermes-upload-<ts>` khác owner → AssignmentError exit 1). Máy chưa có
   `config-machine-N.yaml` → copy config máy 35, sửa `machine: "N"`.
6. Mỗi máy single-machine chạy bằng 1 `terminal(background=true)` riêng — KHÔNG
   gom vòng lặp trong 1 shell (worker con chết theo shell cha).