# Case UI-56: Post-Tap Modal Dialog / Facebook Permission Occlusion & Premature Identity Mismatch

## Bối cảnh & Hiện trường sự cố
- **Máy:** 49 | Serial: `ce041604b3d0c10503` | Nick: `hiencao179`
- **Quy trình:** Follow TikTok (`tiktok-follow`)
- **Triệu chứng:** `MANUAL_REVIEW: exact profile identity không khớp sau tap`
- **Hiện trường UI:** TikTok hiển thị modal dialog xin quyền:
  > *"Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn? Thông tin này sẽ được sử dụng để cải thiện trải nghiệm TikTok cho bạn... Tìm hiểu thêm trong Trung tâm trợ giúp"*
  > Nút: `Không cho phép` (trái) và `OK` (phải). Phía sau popup là profile/suggested accounts.

## Bản chất kiến trúc: Automation-Core vs Consumer Follow Runner
- **Tại sao người dùng nhớ "đã fix ở automation core"?**
  Trong `automation-core` (`automation_core/tiktok_popup.py`), ĐÃ CÓ sẵn rule `facebook_contacts_email_permission_vi`:
  ```python
  PopupRule(
      "facebook_contacts_email_permission_vi",
      ("truy cập vào email và danh sách bạn bè", "danh sách bạn bè trên facebook"),
      PopupAction.TAP,
      _text("Không cho phép"),
  )
  ```
  Và trong `tiktok-follow` (`follow_runner/core/popup.py`), `PopupHandler.contacts_permission()` đã uỷ quyền sang `automation_core.tiktok_popup.dismiss_popup`.
- **Vì sao lỗi vẫn xảy ra ở `tiktok-follow`?**
  Lỗi nằm ở thứ tự thực thi trong `follow_runner/flows/verify_follow.py` tại hàm `verify_after_tap`:
  ```python
  reloads_done = 0

  # 1. recapture MỚI sau tap (KHÔNG check dump cũ)
  cls = classifier(_dump())
  if cls == "followed":
      return _confirm_not_released()
  if cls == "identity_mismatch":
      return VerifyResult("manual", "MANUAL_REVIEW: exact profile identity không khớp sau tap")
  ```
  Khi vừa tap nút Follow, TikTok lập tức bật modal popup Facebook xin quyền email/bạn bè che đè lên màn hình profile.
  Hàm `verify_after_tap` dump UI ngay lập tức và đưa vào `classifier(_dump())` (`_classify_exact_profile_action`) **mà chưa hề gọi `_dismiss()`**.
  Do modal popup che mất profile header handle (`@username`), bộ phân loại kết luận `identity_mismatch`.
  Dòng `if cls == "identity_mismatch"` lập tức trả về `MANUAL_REVIEW: exact profile identity không khớp sau tap` và kết thúc session luôn.
  Hàm `_dismiss()` (và `PopupHandler.contacts_permission` / `dismiss_popup` của `automation-core`) **chưa từng được gọi một lần nào** trong nhánh này.

## Quy tắc xử lý chuẩn (Fix Pattern)
1. **Popup Dismiss Guard trước hoặc khi Identity Mismatch sau Tap**:
   Trong `verify_after_tap`, nếu `cls == "identity_mismatch"` (hoặc khi dump sau tap phát hiện có modal popup/dialog che phủ), BẮT BUỘC phải gọi `_dismiss()` (nếu `popup_dismiss` được truyền vào) để giải phóng dialog trước:
   ```python
   cls = classifier(_dump())
   if cls == "identity_mismatch" and popup_dismiss is not None:
       _dismiss()
       time.sleep(1.0)
       cls = classifier(_dump())
   ```
2. **Bảo toàn tính Fail-Closed**:
   Nếu sau khi đã gọi `_dismiss()` mà dump mới vẫn là `identity_mismatch` (profile thực sự không khớp, không phải do popup che), lúc đó mới an toàn trả về `MANUAL_REVIEW: exact profile identity không khớp sau tap`.
3. **Focused Unit Test**:
   Tạo fixture test trong `test_verify_follow.py`:
   - Trạng thái 1: Dump ngay sau tap chứa popup Facebook / che header handle -> `classifier` trả về `identity_mismatch`.
   - `_dismiss()` được gọi -> popup biến mất, header handle xuất hiện trở lại với nút `Đã follow` / `Nhắn tin`.
   - `verify_after_tap` tiếp tục xác minh thành công (`status == "success"`) thay vì fail-closed vội vàng.
