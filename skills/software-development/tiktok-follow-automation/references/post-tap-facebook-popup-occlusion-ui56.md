# Case UI-56: Post-Tap Facebook / Permission Popup Occlusion & Identity Mismatch

## 1. Triệu chứng & Hiện trường (Máy 49 - 2026-09-07)
- **Log / Alert**:
  - `Script: tiktok-follow`
  - `status: MANUAL_REVIEW`
  - `reason: MANUAL_REVIEW: exact profile identity không khớp sau tap`
  - `followed_count: 13, failed: 1`
- **Màn hình thực tế**:
  - TikTok bung popup modal xin quyền Facebook:
    *"Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn?..."*
    Nút bấm: `"Không cho phép"` (trái) và `"OK"` (phải).
  - Popup này nằm đè lên giao diện Profile, che khuất hoàn toàn cụm header `@username` phía trên (`top_y < 650`).

## 2. Root Cause Analysis
Trong `verify_follow.py` (`verify_after_tap`):
```python
# 1. recapture MỚI sau tap (KHÔNG check dump cũ)
cls = classifier(_dump())
if cls == "followed":
    return _confirm_not_released()
if cls == "identity_mismatch":
    return VerifyResult("manual", "MANUAL_REVIEW: exact profile identity không khớp sau tap")
```
- Khi vừa tap nút Follow, TikTok hiển thị popup xin quyền Facebook.
- `verify_after_tap` gọi ngay `cls = classifier(_dump())` **trước khi gọi bất kỳ hàm dismiss popup nào**.
- `_classify_exact_profile_action(xml, uid)` phân tích XML uiautomator: do popup che khuất header node, không tìm thấy header handle `@uid` hợp lệ thuộc package TikTok, dẫn đến trả về `"identity_mismatch"`.
- Nhánh `if cls == "identity_mismatch":` kích hoạt ngay lập tức và return fail-closed `MANUAL_REVIEW` mà **không hề gọi `_dismiss()`**.
- Mặc dù `PopupHandler` (`popup.py`) và `automation_core.tiktok_popup` đã có sẵn rule `facebook_contacts_email_permission_vi` ("truy cập vào email và danh sách bạn bè" -> tap "Không cho phép"), nhưng cơ chế này không bao giờ được kích hoạt do luồng verify bị short-circuit quá sớm.

## 3. Quy tắc Fix chuẩn
1. **Gọi `_dismiss()` trước khi kết luận `identity_mismatch` / `unknown`**:
   - Khi `cls in ("identity_mismatch", "unknown")`, nếu có `popup_dismiss` được inject vào, bắt buộc gọi `_dismiss()` để xử lý các popup che màn hình (Facebook friends, danh bạ, location, v.v.).
   - Sau khi `_dismiss()` chạy, dump lại uiautomator XML và re-classify lại:
     ```python
     cls = classifier(_dump())
     if cls in ("identity_mismatch", "unknown") and popup_dismiss is not None:
         _dismiss()
         cls = classifier(_dump())
     ```
   - Nếu sau khi dismiss popup mà `cls` chuyển thành `followed`, tiến hành `_confirm_not_released()` như bình thường.
   - Nếu vẫn là `identity_mismatch`, lúc này mới an toàn kết luận là profile sai thật và trả về `MANUAL_REVIEW`.

2. **Dọn dẹp popup trong `_confirm_not_released()`**:
   - Sau thao tác `pull_to_refresh_profile`, TikTok cũng có thể bật popup bất ngờ. Nếu kết quả sau refresh không phải `followed` hay `not_followed`, cũng cần gọi `_dismiss()` và re-check trước khi báo lỗi nút không xác định.

3. **Bảo toàn tính toàn vẹn của PopupHandler**:
   - Đảm bảo `self.decline()` (với markers `POPUP_DECLINE = ("Từ Chối", "TỪ CHỐI", "Từ chối", "Không cho phép")`) và `self.contacts_permission()` xử lý dứt điểm popup Facebook bằng cách bấm "Không cho phép" và kiểm tra `_popup_gone`.
