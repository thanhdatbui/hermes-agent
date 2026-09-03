# Profile Verification Camera False Positive & Back Key Navigation Drop

## Hiện tượng (Incident)
Đồng loạt nhiều máy bị lock `blocked` với lỗi:
`profile verification mismatch: profile account mismatch (detected: None, expected: <username>)`
dù trước đó lướt feed hoàn thành 100% (8–11 swipes).

## Nguyên nhân gốc (Root Cause)
1. Trong luồng `_verify_profile_after_session`, sau khi lướt feed, script điều hướng vào trang Hồ sơ (Profile tab).
2. Trước khi đọc username từ UI XML, script gọi các bộ lọc popup/overlay trong `benign_popup_registry.py`, trong đó có `_detect_camera_creation`.
3. Hàm `_detect_camera_creation` kiểm tra nếu XML/OCR chứa từ 2 từ khóa trở lên trong `["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "CAMERA"]`.
4. **Màn hình Hồ sơ chuẩn của TikTok luôn chứa:**
   - Text "Ảnh hồ sơ" (khớp từ khóa `ẢNH` / `Photo`)
   - Nút icon "Camera" tạo nhật ký (khớp từ khóa `CAMERA`)
5. Do khớp 2 từ khóa, `_detect_camera_creation` trả về `True` (False Positive) ngay trên trang Hồ sơ chuẩn!
6. Bộ gỡ `_dismiss_camera_creation` tự động gửi phím `KEYCODE_BACK` để "tắt camera".
7. Lệnh `BACK` khiến TikTok điều hướng thoát khỏi trang Hồ sơ, quay trở lại Bảng tin (FYP).
8. Khi script đọc XML để đối soát username, trên Bảng tin không có username hồ sơ -> `detected: None` -> đánh giá nhầm là `profile account mismatch` và kích hoạt khóa giữ hiện trường (`status: blocked`) hàng loạt.

## Quy tắc khắc phục & phòng ngừa (Prevention Rules)
1. **Exclude Profile Screen Elements:** Bộ nhận diện Camera Creation (`_detect_camera_creation`) BẮT BUỘC phải loại trừ (bỏ qua) nếu màn hình đã có các thành phần đặc trưng của trang Hồ sơ:
   - "Đã follow", "Follower", "Thích", "Sửa hồ sơ", "Thêm tiểu sử", "Menu hồ sơ", "Cài đặt và quyền riêng tư", `@...`.
2. **Yêu cầu Timer / Mode markers thực sự của Camera:**
   - Không được chỉ dựa vào cặp từ chung "Ảnh" + "Camera".
   - Bắt buộc phải có các từ khóa độc quyền chế độ quay/chụp: `"15s"`, `"60s"`, `"10 phút"`, `"10m"`, `"Mẫu"`, `"Templates"`, `"Tốc độ"`, `"Hiệu ứng"`, `"Lật"`.
3. **Phòng tránh False Mismatch Lockout:** Khi `verify_profile` nhận diện mismatch (`detected: None`), kiểm tra lại xem màn hình hiện tại có thực sự là Profile tab hay đang ở FYP/trang khác trước khi kết luận và giữ lock.
