# Case: Profile Username Still Mismatched After Switch (Feed Drift Regression)

## Triệu chứng
- Alert dừng máy: `profile username still mismatched after switch`
- Xảy ra hàng loạt sau khi đổi nick trong Account Switcher (Bottom Sheet).
- Hiện trường máy thật: TikTok đang ở **Trang chủ / Đề xuất (For You Feed)** với một video creator bất kỳ (ví dụ `@Linhnguyen1707`).

## Nguyên nhân gốc rễ (Root Cause)

1. **TikTok văng về Feed sau khi Switch:**
   - Khi tap chọn tài khoản trong Account Switcher, TikTok nạp lại phiên và tự động đưa màn hình về Home / For You feed.
   - Cú tap điều hướng tab Hồ sơ (`tap_navigation_target`) diễn ra trong lúc TikTok đang chuyển cảnh hoặc reload nên bị drop/nuốt tap, app vẫn ở lại For You feed.

2. **Hàm `_profile_guard_drifted_from_profile` nhận diện drift sai:**
   - Đoạn code cũ yêu cầu `xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS`:
     ```python
     # ❌ LỖI:
     if "keyboard cleanup" in reason:
         return True
     return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
     ```
   - Khi dump XML sạch (`xml_error == ""`), hàm trả về `False` dù `detected` đang là `"home"` hoặc `"for-you"`.
   - Flow không nhận diện được app đã drift khỏi Profile, trôi xuống `read_profile_identity()`.

3. **Đọc nhầm `@creator` video làm Username tài khoản:**
   - `read_profile_identity` phân tích XML của For You feed như thể là trang Profile.
   - Regex tìm chuỗi bắt đầu bằng `@` quét trúng `@creator` trong caption video (ví dụ `@Linhnguyen1707`), gán làm `username`.
   - `verify_and_switch_profile` so sánh `@creator` với nick mong đợi (`expected`) $\rightarrow$ mismatch $\rightarrow$ dừng phiên với `profile username still mismatched after switch`.

4. **Lưu ý số dòng (Row Index) trong Workbook:**
   - Trong `taikhoan_run_safe.xlsx`, một máy có thể chứa tối đa 5-6 tài khoản được đánh số từ Row 1 đến Row 6.
   - Farm Alert có thể xảy ra ở Row 6 (ví dụ nick `ruffumyxkvv`), trong khi câu lệnh Canary test mẫu thường mặc định `-Row 1` (ví dụ nick `shirldlpbkg`). Cần kiểm tra đúng Row của tài khoản mục tiêu trước khi đánh giá kết quả canary.

## Giải pháp chuẩn hóa (Case Fix)

1. **Khẳng định Drift khi ở Feed Screens:**
   Trong `_profile_guard_drifted_from_profile(row)`:
   ```python
   if detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:
       return True
   ```
   Luôn xác nhận `True` khi `detected` thuộc các màn hình feed, không phụ thuộc vào `xml_error`.

2. **Kích hoạt Re-tap Profile khi Drift:**
   Trong `_read_profile_identity_with_add_phone_guard`:
   ```python
   if _is_degraded_xml_drift(guard_row) or str(guard_row.get("detected") or "") in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:
       _recovered_row = _try_profile_retap_on_drift(ctx, guard_row, guard_step)
       if _recovered_row is not None:
           return _recovered_row
   ```
   Tự động re-tap tab Profile để kéo app về trang cá nhân thay vì tiếp tục đọc danh tính trên For You feed.
