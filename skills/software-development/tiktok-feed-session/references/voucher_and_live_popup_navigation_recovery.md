# Voucher & TikTok LIVE Popup Multi-Layer Navigation Recovery

## 1. Triệu chứng & Bối cảnh
- **Lỗi:** `profile verification navigation-failed: navigation target profile not found in XML` hoặc timeout/fail tại bước `tap_navigation_target` / `_navigate_profile_for_preflight` / `_verify_profile_after_session`.
- **Hiện trường:** Thiết bị hiển thị popup modal nhận Voucher (ví dụ: "Nhận voucher giảm giá", "Giảm 60K đ", nút đỏ "Nhận" và nút đóng "✕") đè lên màn hình phòng TikTok LIVE PK split-screen hoặc LIVE stream.
- Thanh bottom navigation bar (Trang chủ / Bạn bè / Hộp thư / Hồ sơ) hoàn toàn bị che khuất khỏi cây UI XML.

## 2. Nguyên nhân gốc rễ (Root Cause)
- Khi `find_matching_handler` trong `calibrate_screens.py` hoặc `feed_swipe_smoke.py` chưa đăng ký nhận diện popup voucher / live room, kịch bản chỉ thử 1 phím BACK đơn lẻ.
- 1 phím BACK chỉ đóng được lớp modal popup Voucher phía trên, nhưng màn hình nền bên dưới vẫn là phòng LIVE / Live PK (vẫn chưa có navigation bar). Cần thêm 1 phím BACK / thoát Live room nữa mới trở về feed video chính có tab bar.

## 3. Kiến trúc giải pháp chuẩn (Standard Pattern)
1. **Đăng ký Handlers trong `flows/benign_popup_registry.py`**:
   - `voucher_discount_popup` (priority 94): Bắt các từ khóa voucher/giảm giá ("nhận voucher giảm giá", "voucher giảm giá", "phiếu giảm giá", "mã giảm giá", "giảm 60k/50k/30k/20k/10k", "voucher discount", v.v.). Đóng nút X/Đóng/Cancel hoặc Back key, sau đó kiểm tra nếu còn phòng Live thì thoát Live.
   - `tiktok_live_room` (priority 85): Nhận diện màn hình LIVE room / LIVE PK khi bottom tab bar bị thiếu. Thoát bằng phím Back key về feed chính.
2. **Quét đa tầng (Multi-layer Check) trong `flows/calibrate_screens.py`**:
   - Trong `tap_navigation_target`: cho phép tất cả các popup handler an toàn trong registry (bao gồm `voucher_discount_popup`, `tiktok_live_room`, `live_campaign_overlay`).
   - Nếu sau khi đóng popup thứ nhất mà vẫn chưa tìm thấy `target`, lập tức quét tiếp `find_matching_handler(retry_xml_text, "")` để xử lý lớp thứ hai (multi-layer popup dismiss).
   - Tăng cường cơ chế Back recovery lên 2 lần liên tiếp với kiểm tra ở giữa.
3. **Phục hồi trong `flows/feed_swipe_smoke.py`**:
   - Tích hợp quét registry popup trong `_maybe_recover_navigation_from_add_phone` (khi `else:` không khớp các case form phone/security thông thường).
   - Tích hợp kiểm tra và đóng registry popup trong `_verify_profile_after_session` trước khi gán `profile_verify_status = "navigation-failed"`.
