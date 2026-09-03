# VIDEO_PICK visual caption-composer fallback khi XML chết (2026-08-10)

## Bối cảnh

Batch 2 (04:04, 24 máy, manifest `assignment-tik1-lowcount-20260809_215614.json`, code có `_ensure_screen_on` + profile-detail navigate) → 11 report đầu: 8× `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED ... Feed was not verified before tap` + 3× `OPEN_TIKTOK_FAILED`.

Probe máy 13 (serial `988678543555413857`, run `run_988678543555413857_20260810_040246`) bằng vision: **màn THẬT đang ở caption composer đầy đủ** — "Thêm mô tả..." + nút Đăng đỏ + Nháp + gợi ý vị trí Đà Nẵng + thumbnail "Xem trước/Sửa ảnh bìa". Tức worker ĐÃ mở composer, chọn video, qua editor — chỉ fail vì verifier không nhận ra màn mình đang đứng.

## Chuỗi log signature (m13)

```
04:07:22 Tapped center create button via screenshot-verified fallback   ← composer MỞ
04:07:37 Waiting for upload screen...
04:07:43 Upload picker screen visible
04:07:55 Chọn tile video bằng duration overlay bounded: (540, 546)      ← video ĐƯỢC CHỌN
04:08:27 [ERROR] Editor Next tapped but caption composer did not open  ← FALSE NEGATIVE
04:08:32 Visual create-button gate rejected: white=0.705, dark=0.000, cyan=0.000, red=0.291
04:08:43 [ERROR] Coordinate create-entry fallback: Feed was not verified before tap
```

Điểm mấu chốt: attempt 2 visual gate `white=0.705, red=0.291` = chính là màn caption composer (form trắng + nút Đăng đỏ), nhưng code nhìn screenshot đó để tìm "create button" (yêu cầu dark≥0.005 cho crop bottom) → reject → tưởng chưa vào composer → coordinate fallback tìm feed → fail oan.

## Root cause

- uiautomator dump 137 toàn farm → `adapter.dump_ui()` trả xml_text rỗng.
- `_is_final_composer_surface(adapter, xml_text)` có `if not xml_text: return False` → không bao giờ nhận composer khi XML chết.
- Mọi classifier dựa XML (feed/detail/action-sheet/caption) đều False → coordinate fallback → "Feed was not verified before tap".

## Fix (code SỐNG, hoàn tất 2026-08-10 — commits `908462f`, `dbd3f07`, `eee3ea0`, full suite 381 pass, COMPAT-VIDEO-PICK-002)

`_visual_caption_composer_likely(adapter)` trong `state_machine.py`:
- Screenshot toàn màn qua `context.device_transport.screenshot(path)` vào `run_dir/video-pick-visual-caption-composer.png`.
- Pixel: `white = min(r,g,b)>220` fraction; red/pink = `r>180 && g<170 && b<200` fraction — **mở rộng hồng sáng `(250,60,110)`** vì nút Đăng build 46 KHÔNG đỏ đậm.
- `likely = white >= 0.40 and (red_full >= 0.08 OR tr_red >= 0.10 OR br_red >= 0.10)` với 3 vùng:
  - toàn màn `red_full` (form trắng + nút Đăng lớn — m13: red=0.291);
  - crop top-right `(70-100%w, 4-22%h)` (build cũ — m13 top-right);
  - crop **bottom-right `(70-100%w, 85-99%h)`** (build 46 — m24: nút Đăng dưới-cùng bên phải, Nháp trái + Đăng phải, màu `(235,90,40)`/hồng `(250,60,110)`, NHỎ → toàn-màn red chỉ 0.030, tr_red=0.000).
- Phân biệt: feed tối (dark cao), profile detail (dark≈0.6), screen-off (dark≈0.97) — tất cả đều không đạt white≥0.40 + vùng đỏ/pink.

Gọi từ `_is_final_composer_surface` 3 nhánh:
1. `if not xml_text: return self._visual_caption_composer_likely(adapter)` (XML chết).
2. `if not has_post_control: return self._visual_caption_composer_likely(adapter)` — XML không có Post control.
3. Sau caption-field check fail: `return self._visual_caption_composer_likely(adapter)`.

## Regression tests (4, file tests/test_tiktok_workflow.py)

- `test_video_pick_final_composer_visual_fallback_when_xml_empty` — ảnh trắng 540×960 + nút đỏ (230,40,40) — **nút phải ≥~9% diện tích (vd 140×360 px = 0.097)**, nút nhỏ 100×60 px = red 0.012 → gate reject dù code đúng (mắc thật).
- `test_video_pick_final_composer_visual_rejects_dark_feed` — ảnh toàn (20,20,20) → False (fail-closed).
- `test_video_pick_final_composer_visual_accepts_small_pink_post_button` — nút hồng (250,60,110) NHỎ top-right → top-right crop ≥0.10 → True.
- `test_video_pick_final_composer_visual_accepts_bottom_right_post_button` — nút đỏ cam (235,90,40) DƯỚI-CÙNG BÊN PHẢI (build 46 m24 thật) → bottom-right crop → True.

⚠️ **PITFALL fixture**: `StateContext(reporter=SimpleNamespace(run_dir=None))` → `_visual_caption_composer_likely` check `if not run_dir: return False` → test fail dù code đúng. Fixture phải tạo `tmp_path` thật và truyền `reporter=SimpleNamespace(run_dir=tmp_path)`.

## Bài học lan rộng

- **Verifier phải có tầng VISUAL khi XML chết, không chỉ semantic**: dump 137 farm-wide là trạng thái phổ biến đêm farm đông — mọi classifier text-only sinh false negative.
- Pixel ratios đã có sẵn pattern (white/dark/cyan/red) trong `_tap_visual_create_button` — tái dùng cùng ngưỡng đã verify, không tự chế ngưỡng mới.
- Khi visual gate reject với `white` CAO + `red` CAO + `dark` ≈ 0: nghi caption composer, đừng kết luận "chưa vào được" — probe vision để xác nhận.
