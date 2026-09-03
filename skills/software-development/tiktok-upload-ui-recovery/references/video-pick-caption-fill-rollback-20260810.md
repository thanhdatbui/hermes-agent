# VIDEO_PICK → CAPTION_FILL XML-chết + git rollback (đêm 09→10/08/2026)

Chuỗi recovery 24 máy fail đồng loạt + bài học user-caught cuối phiên (revert git
về bản trước fix máy 74). Bổ sung cho §14d (video-pick batch fail 2026-08-09/10).

## 1. Nút Đăng vị trí KHÁC NHAU theo build — visual gate crop CẢ top-right lẫn bottom-right

- Build cũ: nút Đăng đỏ đậm GÓC TRÊN-PHẢI → crop (70-100%w, 4-22%h).
- Build 46 (m24 live 04:34, artifact `video-pick-visual-caption-composer.png` +
  vision xác nhận): nút **Đăng đỏ cam DƯỚI-CÙNG BÊN PHẢI** (Nháp trắng bên trái),
  nút nhỏ + màu hồng sáng (250,60,110) không phải đỏ đậm.
- Số liệu thật m24: `white=0.865, red=0.030 toàn màn, tr_red=0.000` — top-right
  crop KHÔNG có gì → gate cũ matched=False dù màn đúng là caption composer.
- Fix (code SỐNG, commit eee3ea0, 381 tests green): detector red/pink mở rộng
  `r>180 and g<170 and b<200`; crop CẢ top-right (70-100%w 4-22%h) HOẶC
  bottom-right (70-100%w 85-99%h) ≥0.10; white toàn màn ≥0.40; dark≈0.00 là
  marker phân biệt với feed (màn form sáng toàn phần).
- Regression: `test_video_pick_final_composer_visual_accepts_bottom_right_post_button`.
- Thứ tự mắc: verifier top-right-only → miss → đọc ảnh thật + vision → bottom-right.
  **Luôn chạy spike ảnh thật (vision) trước khi chốt vị trí nút**, không đoán layout.

## 2. CAPTION_FILL chết khi XML chết — coordinate tap field + typing thẳng

- Máy 24 QUA được VIDEO_PICK bằng visual gate (composer nhận đúng) nhưng fail
  `Caption field not found via selectors` ×3 (attempt 1/3..3/3).
- Root cause: `_find_caption_field`, `_clear_caption_input`, VÀ
  `_fill_caption_typing_fallback` chunk-verify ĐỀU dựa dump_ui XML — uiautomator
  137 farm-wide → xml rỗng → cả chuỗi semantic chết dù màn đúng là composer.
- Fix 2 tầng (code SỐNG, commit 6381897 + 5a96177, 383 tests green):
  (a) CAPTION_FILL: field None + `_is_final_composer_surface` visual True →
      coordinate tap (0.28w, 0.13h scale wm size) — layout "Thêm mô tả..."
      x≈30-580, y≈200-300 / 1080x1920; bỏ `_clear_caption_input` (XML chết;
      field trống vì composer vừa mở video mới).
  (b) `_type_caption_coordinate`: tap field → `adb shell input text` từng chunk
      (CAPTION_TYPING_CHUNK_SIZE=400), verify = command ack (không chunk-verify
      XML được), typing ratio cuối nếu XML sống.
  Helper mới: `_video_pick_screen_size` (wm size Override > Physical).
- Regression: `test_caption_fill_coordinate_fallback_when_xml_dead_and_visual_composer`,
  `test_caption_fill_type_coordinate_when_xml_dead`.
- An toàn: coordinate tap CHỈ khi visual gate đã confirm composer; không tap mù,
  không đăng caption rỗng (verifier ratio giữ fail-closed).

## 3. Unit-green ≠ machine-success — verify END-TO-END 1 máy TRƯỚC khi commit layer kế

- Chuỗi 6 commit fix liên tiếp đêm 09→10/08: 1a34aca (screen-off) → 908462f
  (visual composer gate) → dbd3f07 (pink) → eee3ea0 (bottom-right) → 6381897
  (caption coordinate tap) → 5a96177 (coordinate typing). Mỗi layer unit-test
  green (379→383 pass) NHƯNG máy thật fail ở layer KẾ TIẾP mỗi lần:
  composer nhận ✓ → caption field không tìm thấy ✗ → clear caption không verify ✗
  → không máy nào POST được.
- User phản ứng: "Đụ mẹ phá kiểu gì h đéo up được cả video" → "quay lại bản git"
  → "Bản trước bản hqua nữa? Trước khi fix máy 74 sáng hqua".
- BÀI HỌC: điều kiện chốt fix = **1 máy chạy hết CAPTION_FILL→POST trên máy
  THẬT**, không phải unit test. Fix nhiều tầng mà không máy nào success = user
  mất niềm tin → rollback. Khi bắt đầu recovery signature mới: spike/verify 1
  máy end-to-end trước, HOẶC giữ các layer trên branch fix riêng, chỉ merge khi
  có máy POST thật.

## 4. Rollback git theo mốc thời gian — quy trình đã verify

- Map mốc user nói ("trước khi fix máy 74 sáng hôm qua") ra commit:
  `2e0b530` = CAPTION_FILL typing fallback m74 (01:48 09/08) → target =
  **cha trực tiếp `f4e4520`** (01:22 09/08). Dùng
  `git log --format="%H %ci %s" <hash>` để xác nhận mốc, `git log -1 <hash>^`
  lấy cha.
- Rollback non-destructive (đã làm, commit `6c3d147`):
  `git revert --no-commit <range>` (vd `1a34aca..5a96177`) → `git revert
  --no-commit 1a34aca` cho commit đầu → verify `git diff <target> --stat` rỗng
  → commit revert + push. Giữ history, không cần consent.
- `git reset --hard` + `push --force` = destructive → Hermes BLOCK chờ user
  consent. Nếu dùng path đó: tạo branch backup trước (`git branch backup-<ts>`),
  trình bày hệ quả rõ ràng, chờ xác nhận — không retry lệnh bị block.

## 5. Đừng hỏi xin phép khi skill đã có rule/handler (user-caught)

- User: "Ủa có rule xử lý Ui r hỏi cái đéo gì v" — khi procedure (ATX kill toàn
  farm, dọn lock stale machine+serial, xóa fingerprint reserved fresh sau khi
  chứng minh an toàn) ĐÃ nằm trong skill này, chạy THẲNG, không hỏi
  "tiến hành luôn nhé?".
- Chỉ dừng hỏi khi: chưa có handler cho signature, cần phá vỡ giới hạn an toàn
  chưa user-approved, hoặc destructive có thể mất dữ liệu (reset --hard, xóa
  entry ACCEPTED, đăng lại video đã live).

## Trạng thái cuối phiên

- Main đã revert về `f4e4520` (chưa force-push — chờ user consent cho reset
  --hard; branch backup `backup-fixes-20260810` giữ hiện trạng).
- Farm sạch: lock 13/24/35/74 đã dọn, không process tiktok_workflow sống.
- Các commit fix đêm nay vẫn nằm trong history (1a34aca..5a96177) — có thể
  cherry-pick lại từng layer khi user quyết định tiếp.