# Bẫy Gallery Picker Chọn Nhầm Ảnh Cũ & Tọa Độ Chuẩn Bottom Sheet TikTok

## 1. Bẫy "Tap Mù Tile 1 (Row 1 Col 1)" Gây Báo Cáo Láo Đổi Avatar
- **Hiện tượng:** Runner báo cáo `AVATAR_SMOKE_SUCCESS` / `FORCED_REPLACED_VERIFIED` với exit code 0, nhưng avatar trên kênh thực tế vẫn là ảnh cũ.
- **Căn nguyên kỹ thuật:**
  - Trong luồng tự động (`state_machine.py`), sau khi push avatar mới vào thiết bị và mở Gallery Picker, runner thường có tọa độ tap cố định vào tile đầu tiên `(6, 222, 269, 488)` (Row 1, Col 1).
  - Tuy nhiên, nếu trên thiết bị có các ảnh chụp màn hình gần đây (screencap phục vụ kiểm tra/telemetry) hoặc MediaStore chưa cập nhật đúng thứ tự timestamp, tile đầu tiên tại Row 1 Col 1 thực chất là **ảnh chụp màn hình cũ của Profile**.
  - Runner tap trúng ảnh screenshot cũ, đưa vào màn hình crop và upload lại chính avatar cũ. Hệ thống ghi nhận "Upload thành công" nhưng thực chất là upload lại ảnh cũ.
- **Quy tắc khắc phục bắt buộc:**
  1. **Purge ảnh rác trước khi push:** Xóa sạch ảnh chụp màn hình và avatar tạm trong `/sdcard/Pictures/` và `/sdcard/DCIM/Camera/` trước khi push file mới (`rm -f /sdcard/DCIM/Camera/avatar_*.jpg /sdcard/Pictures/*.png`).
  2. **Định vị tile có kiểm chứng:** Không tap mù `(Row 1, Col 1)`. Phải kiểm tra lưới ảnh (ví dụ 4 cột x 6 hàng) hoặc dùng OCR/Vision để xác nhận đúng tile ảnh mục tiêu (ví dụ trường hợp tile nằm ở Row 3 Col 4).
  3. **Hậu kiểm Visual Diff thực tế:** CẤM TUYỆT ĐỐI tin tưởng mù quáng vào status `AVATAR_SMOKE_SUCCESS` hay `exit code 0` của runner. BẮT BUỘC chụp lại màn hình Profile, cắt vòng tròn avatar và đối soát độ tương đồng (perceptual diff / OCR) với ảnh nguồn trước khi báo cáo User.

---

## 2. Tọa Độ Chuẩn Màn Hình "Sửa Hồ Sơ" & Bottom Sheet Đổi Ảnh
- **Truy cập Sửa hồ sơ:**
  - Nếu có nút chữ: Tap `Sửa hồ sơ` tại khoảng `(380, 680)`.
  - Nếu layout icon: Tap icon cây bút chì cạnh username tại `(75, 150)`.
- **Mở Bottom Sheet:**
  - Tap chữ `Thay đổi ảnh` tại tâm `(539, 579)` (bounds `[394, 554, 684, 605]`).
  - *Lưu ý:* Tránh tap vào camera icon ở `(540, 380)` vì một số phiên bản TikTok có thể kích hoạt Face Liveness / Camera quét mặt thay vì mở thư viện.
- **Tọa độ các nút trong Bottom Sheet (1080x1920):**
  - `Chụp ảnh`: `(200, 1480)` (bounds `[49, 1454, 357, 1508]`).
  - `Tải ảnh lên` (Mục tiêu chọn ảnh từ máy): **`(224, 1637)`** (bounds `[51, 1613, 397, 1661]`).
    * *Cảnh báo:* CẤM tap mù vào giữa `(540, 1720)` vì sẽ hụt hoặc bấm nhầm nút khác.
  - `Xem ảnh`: `(200, 1790)` (bounds `[50, 1770, 340, 1816]`).
- **Màn hình Cắt (Crop):**
  - Nút `Lưu` (Save): Nút màu hồng/đỏ ở góc dưới phải tại **`(792, 1794)`** (bounds `[552, 1728, 1032, 1860]`).
  - Nút `Hủy` (Cancel): Nằm ở góc dưới trái.
