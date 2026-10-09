# Profile Switcher Drift Recovery & Account Mismatch Phòng Chống Regression

## Bối cảnh & Triệu chứng lỗi
- **Hiện tượng:** Hàng loạt máy dừng phiên sau bước chuyển tài khoản với lỗi `profile username still mismatched after switch`.
- **Dấu vết hiện trường:** Màn hình máy thực tế không ở trang Profile mà bị rơi về **Trang chủ / Đề xuất (For You Feed)** hoặc các tab feed khác (`home`, `following`, `friends`).

## Cơ chế lỗi cốt lõi (Anti-Pattern)
1. **TikTok Default Navigation sau Switch:** Khi chọn tài khoản trong Account Switcher bottom sheet, TikTok khởi tạo lại session và tự động đưa app về trang Home Feed.
2. **Dropped Navigation Tap:** Cú tap tab Hồ sơ (`tap_navigation_target(_profile_target())`) ngay sau đó bị trễ nhịp animation hoặc uiautomator settle khiến tap bị nuốt, app vẫn ở lại Feed.
3. **Flawed Drift Detection:** Hàm `_profile_guard_drifted_from_profile` kiểm tra:
   ```python
   # ❌ LỖI REGRESSION:
   if "keyboard cleanup" in reason:
       return True
   return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
   ```
   Khi UI XML dump thành công và sạch (`xml_error == ""`), hàm trả về `False` dù màn hình đang rõ ràng là `home` / `for-you`!
4. **False Profile Identity Parsing:** Do không nhận diện được là app đã trôi về Feed, flow gọi `read_profile_identity()`. Tại Feed, parser đọc trúng `@creator` trong caption video (hoặc creator watermark) và coi đó là username hiện tại của máy $\rightarrow$ so sánh lệch với nick dự kiến $\rightarrow$ fail-closed với `profile username still mismatched after switch`.

## Giải pháp Chuẩn (Standard Fix)
1. **Strict Positive Drift Detection:**
   Trong `_profile_guard_drifted_from_profile`: Khi `detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}`, bắt buộc trả về `True` ngay lập tức, bất kể `xml_error` có hay không.
2. **Re-tap Profile Recovery:**
   Trong `_read_profile_identity_with_add_phone_guard`: Khi phát hiện drift về Feed (`str(guard_row.get("detected") or "") in {"home", ...}`), kích hoạt `_try_profile_retap_on_drift` để re-tap tab Hồ sơ kéo app trở về đúng màn hình Profile trước khi đọc identity.

## Kỷ luật Điều phối (Coordinator vs Worker)
- Khi user cảnh báo "Ms sửa hàm gì gây lỗi này hàng loạt máy r đó":
  - Kiểm tra ngay `git log` các commit gần nhất đụng vào file/hàm liên quan (`feed_swipe_smoke.py`, account switcher, identity guard).
  - Khoanh vùng nhánh điều kiện nào vừa bị sửa làm đảo ngược logic (ví dụ nhánh negative check hoặc bypass check).
  - Không tự viết script chạy mò trong session chính; soạn Patch Contract rõ ràng và dispatch Worker Subagent xử lý trong background.
