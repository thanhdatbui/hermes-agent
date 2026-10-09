# Profile Switcher Network Error & Settle Recovery

## Hiện tượng (Symptom)
Khi thực hiện switch account trong `verify_and_switch_profile` (`feed_swipe_smoke.py`), sau khi đã tap chọn tài khoản chính xác từ account switcher modal (`selected_account_by_exact_switcher = True`), TikTok thường gặp 2 vấn đề:
1. **Lỗi mạng tạm thời / Đã xảy ra lỗi**: Màn hình profile hiển thị thông báo "Đã xảy ra lỗi" / "Thử lại sau" kèm nút "Thử lại" (`resource-id`: `com.ss.android.ugc.trill:id/dcj`, text `Thử lại`, bounds ~ 540, 1436 trên 1080x1920). Profile không thể tải dữ liệu của account mới.
2. **Lag settle / UI transition delay**: TikTok giữ thông tin profile của account cũ trong 1–3 giây trước khi thực sự cập nhật sang account mới.

Nếu script chỉ đọc identity một lần duy nhất ngay sau switch, username đọc được vẫn là account cũ -> dẫn tới fail ngay với lý do `profile username still mismatched after switch`.

## Quy tắc xử lý chuẩn (Recovery Pattern)
1. **Kiểm tra màn hình lỗi sau switch**:
   - Quét XML / UI dump xem có text `Đã xảy ra lỗi`, `Thử lại sau`, `Thử lại`, hoặc ID `com.ss.android.ugc.trill:id/dcj`.
   - Nếu có nút `dcj` / text `Thử lại`: tap retry (nút hoặc fallback coordinate ~ 540, 1436) và chờ settle 2-3s.
2. **Settle delay khi vừa tap exact switcher**:
   - Nếu `not verified` nhưng `selected_account_by_exact_switcher == True`, cho phép settle 2.0 - 3.0s rồi re-capture / re-read identity (`_read_profile_identity_with_add_phone_guard`).
3. **Re-verify trước khi fail**:
   - Thử lại `verify_selected_account` hoặc so khớp username/display_name với expected.
   - Chỉ gán `last_reason = "profile username still mismatched after switch"` khi sau retry/settle mà vẫn không khớp.
