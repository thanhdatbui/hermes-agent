# Lessons Learned: Bẫy Blind Tapping Tọa Độ Top-Left (75, 150) & Cú Lừa Tìm Kiếm Bạn Bè Trên TikTok S7

## 1. Hiện Tượng Thực Tế
Khi điều khiển giao diện TikTok Android (bản v47.x trên Samsung S7 độ phân giải 1080x1920) để thực hiện đổi Tên hiển thị (Display Name):
- Script tự động tap mù vào tọa độ `(75, 150)` với suy nghĩ đây là nút Back/Quay lại.
- Trên thực tế:
  * Góc trên bên trái của trang **Hồ sơ (Profile)** là icon **"Tìm bạn bè / Thêm bạn" (Find Friends)** (hình người có dấu `+`), hoàn toàn không phải nút Quay lại.
  * Cú tap vào `(75, 150)` mở màn hình **Tìm bạn bè**.
  * Thanh Search trên cùng tự động được chọn (focused).
  * Lệnh gõ tên mới tiếp theo qua `AdbKeyboard` gõ thẳng chuỗi tên (ví dụ: `Hải Cường`) vào ô Search và tự động kích hoạt tìm kiếm!
  * Màn hình TikTok hiển thị:
    - Search box: `Hải Cường`
    - Nội dung giữa màn hình: **`Không tìm thấy kết quả`**
    - Đáy màn hình: Bàn phím AdbKeyboard hiển thị 4 nút: `[∞] [Clear Text] [Search] [Switch IME]`.

## 2. Hậu Quả & Rủi Ro Nghiêm Trọng
- Script không có khâu OCR Readback Verification:
  * Chụp ảnh màn hình "Không tìm thấy kết quả" nhưng vẫn ngộ nhận là đã đổi tên thành công.
  * Báo cáo ảo hoàn tất lên hệ thống trong khi tên nick không hề đổi.

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Anti-Blind Tapping Invariant)
1. **Tuyệt đối cấm tap mù tọa độ**:
   - CẤM gọi `tap(75, 150)` trên màn hình Profile.
   - Để vào trang Sửa hồ sơ, BẮT BUỘC dùng OCR tìm text `Sửa hồ sơ` / `Chỉnh sửa hồ sơ` (`(210, 865)`) hoặc icon cây bút chì bên phải dòng tên `(870, 558)`.
2. **State-Machine 5 Trạng Thái Khép Kín**:
   - `FEED` -> tap tab Hồ sơ `(972, 1857)`.
   - `PROFILE` -> đọc `nickname_on_profile`. Nếu chưa đúng acc mục tiêu thì mở Switcher.
   - `EDIT_PROFILE` -> OCR tìm dòng có chữ "Tên" rồi mới tap mở ô sửa tên.
   - `NAME_EDIT` -> gõ AdbKeyboard -> BẮT BUỘC đọc lại OCR kiểm tra tên mới + bộ đếm ký tự `{len}/30` -> tap Lưu `(980, 140)`.
   - `PROFILE (Readback)` -> Trở lại Profile, OCR đọc lại dòng ngay trên `@username`. Chỉ khi tên thật trên Profile khớp 100% với tên mới thì mới lưu trạng thái hoàn thành.
