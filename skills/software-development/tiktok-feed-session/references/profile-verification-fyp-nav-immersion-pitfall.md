# Profile Verification FYP Nav Immersion Pitfall & Mass Lock Root Cause

## Triệu chứng
- Hàng loạt máy (20-30+ máy) sau khi hoàn thành lượt swipe feed (8-11 swipes) đồng loạt bị khóa giữ hiện trường với trạng thái `status: blocked` / `manual-needed`.
- Log báo: `"stop_reason": "profile verification mismatch: profile account mismatch"`, `"expected": "<username>", "detected": null`.

## Nguyên nhân gốc (Root Cause)
1. **TikTok Immersive Fullscreen Mode:** Khi kết thúc vòng lặp swipe, video TikTok đang phát ở chế độ toàn màn hình (FYP), thanh điều hướng dưới đáy (Bottom Navigation Bar) bị ẩn hoặc chiếm bởi overlay video/nhạc.
2. **Tap Profile bị trượt:** Lệnh chạm vào tọa độ icon Hồ sơ (ví dụ `[972, 1857]`) chạm trúng video/overlay hoặc không kích hoạt chuyển tab Profile, màn hình vẫn ở trang Đề xuất (For You Feed).
3. **Phán đoán nhầm `profile account mismatch`:** Script chụp XML/UI để đọc `profile_username`, nhưng vì đang ở FYP nên không có trường username (`detected = null`). Bộ so sánh kết luận sai tài khoản và kích hoạt `preserve_blocker_screen`, tự động khóa máy giữ hiện trường hàng loạt.

## Hướng xử lý & Quy chuẩn
1. **Kiểm tra UI trước khi đọc Profile:**
   - Trước khi trích xuất username, BẮT BUỘC kiểm tra màn hình hiện tại có thực sự là tab Hồ sơ (chứa `Edit profile` / `Sửa hồ sơ`, `Followers`, `Following`, icon menu 3 gạch hoặc resource-id của trang Profile) hay chưa.
   - Nếu màn hình vẫn là FYP / Feed, thực hiện tap/swipe nhẹ để đánh thức thanh điều hướng dưới đáy trước khi tap icon Profile, hoặc thử lại tap với fallback tọa độ an toàn.
2. **Phân biệt `detected = null` do chưa chuyển màn hình vs `detected != expected` do sai account:**
   - Nếu không ở trang Profile (`detected = null`), ghi nhận lỗi điều hướng/UI (`nav_profile_failed`), không được gán nhãn `profile account mismatch` để tránh kích hoạt cấm chạy diện rộng.
