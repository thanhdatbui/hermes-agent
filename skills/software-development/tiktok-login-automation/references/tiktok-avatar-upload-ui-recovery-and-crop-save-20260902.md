# TikTok Avatar Upload UI Recovery, Crop Screen & Account Switcher Selection (2026-09-02)

## 1. Màn hình Crop Avatar & Xử lý Nút Lưu / Nhật ký Story
Trên TikTok layout mới (Samsung S7 1080x1920):
- Sau khi chọn ảnh từ thư viện (`/sdcard/Pictures/av_...jpg`) và bấm Tiếp (`Tiếp (1)` tại `924, 1842` hoặc `o_9`/`xip`), màn hình Crop (`Cắt`) xuất hiện.
- **Checkbox Đăng lên Nhật ký:** Checkbox `com.ss.android.ugc.trill:id/sca` mặc định được tick (`bounds [48,1554][120,1626]`).
  - Phải uncheck trước khi lưu: tap center `(84, 1590)`.
- **Nút Lưu / Lưu và đăng:**
  - Nút `Lưu` ở chân trang: bounds `[552,1728][1032,1860]` -> tap center **`(792, 1794)`**.
  - Nếu hiện prompt xác nhận "Lưu và đăng": tap **`(540, 1764)`** rồi confirm **`(792, 1794)`**.

## 2. Scroll Top Profile để tránh mất nút Sửa hồ sơ / Bút chì
- Khi script scan lưới video đếm baseline (bước `ACCOUNT_READY`), trang Profile bị cuộn lửng làm trôi nút Sửa hồ sơ / Bút chì (`[777,510][921,594]`, center `849, 552`).
- Script không tìm thấy nút sẽ fallback sang deep-link `snssdk1233://profile/edit` và bị TikTok chặn popup *"Hoạt động không có sẵn"*.
- **Fix bắt buộc:** Luôn vuốt cuộn 2 lần về đỉnh trang (`input swipe 540 400 540 1500 300`) trước khi tìm nút Sửa hồ sơ hoặc tap bút chì `(849, 552)`.

## 3. Account Switcher trên Profile Root mới
- Khi cần chuyển sang đúng nick mục tiêu (ví dụ máy đang login sẵn nick khác):
  - Tap anchor tên user ở góc trên bên trái `[36,249][223,330]` (center **`(140, 300)`**) để mở Bottom Sheet "Chuyển đổi tài khoản".
  - Tìm node text chứa `@username` mục tiêu trong danh sách và tap để chuyển.
  - Sau khi chuyển, tap lại tab Hồ sơ `(972, 1857)` và vuốt cuộn về đầu trang.
