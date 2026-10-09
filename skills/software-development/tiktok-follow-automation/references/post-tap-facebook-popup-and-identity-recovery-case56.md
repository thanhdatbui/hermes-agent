# Case UI-56: Post-Tap Popup Dismiss & Header Identity Recovery in verify_after_tap

## Hiện trường sự cố (Farm Alert Máy 49)
- **Script:** Follow TikTok (`tiktok-follow`) tại `D:/Taadaa/tiktok-follow`
- **Máy:** 49 | Serial: `ce041604b3d0c10503` | Nick: `hiencao179` | Ca: Row 1
- **Triệu chứng:** `MANUAL_REVIEW: exact profile identity không khớp sau tap`
- **Màn hình hiện trường:** Màn hình TikTok hiển thị modal popup xin quyền Facebook: *"Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn?..."* với 2 nút "Không cho phép" (trái) và "OK" (phải), che khuất header profile phía sau.

## Root Cause (Nguyên nhân gốc rễ)
1. Trong `verify_follow.py` (`verify_after_tap`), ngay sau khi bấm Follow một tài khoản, TikTok có thể lập tức bật popup modal Facebook xin quyền kết nối email và bạn bè.
2. Runner lập tức gọi `cls = classifier(_dump())` để xác thực lại profile header `@uid` (`y < 650`) trước khi gọi bất kỳ hàm dismiss popup nào.
3. Vì modal popup che mất profile header, hàm `_classify_exact_profile_action` không tìm thấy header `@uid` khớp và trả về `"identity_mismatch"`.
4. Code cũ gặp `"identity_mismatch"` lập tức fail-closed trả về `MANUAL_REVIEW: exact profile identity không khớp sau tap` mà không cho phép `popup_dismiss` chạy.

## Giải pháp chuẩn (Case Fix)
1. Trong `verify_after_tap`, trước khi vội vàng phán quyết `identity_mismatch`, nếu `popup_dismiss` có sẵn, chủ động gọi `_dismiss()`:
   ```python
   # 1. recapture MỚI sau tap (KHÔNG check dump cũ)
   cls = classifier(_dump())
   if cls == "identity_mismatch" and popup_dismiss is not None:
       _dismiss()
       cls = classifier(_dump())
   if cls == "followed":
       return _confirm_not_released()
   if cls == "identity_mismatch":
       return VerifyResult("manual", "MANUAL_REVIEW: exact profile identity không khớp sau tap")
   ```
2. Thêm button suffix `:id/flp` và `id/flp` vào `_ACTION_BUTTON_SUFFIXES` nếu TikTok cập nhật layout mới.
3. Bổ sung unit test hồi quy `test_identity_mismatch_dismisses_popup_and_reclassifies` trong `follow_runner/tests/test_verify_follow.py`.

## Điều phối Coordinator & Worker (Patch Contract Lesson)
- Khi gặp Farm Alert mà worker subagent có nguy cơ chạy lan man hoặc cạn tool calls khảo sát rộng, Coordinator BẮT BUỘC soạn sẵn **Patch Contract cơ học (grep -c=1)**:
  - Ghi rõ đường dẫn file cần sửa.
  - Cung cấp chính xác khối code `old_string` và `new_string`.
  - Cung cấp code unit test cụ thể.
  - Cung cấp lệnh chạy focused test và canary test với budget nghiêm ngặt (<= 6 calls, <= 5 phút).
- Điều này giúp worker subagent thực thi dứt điểm trong 1 lượt mà không làm kéo dài thời gian xử lý farm.
