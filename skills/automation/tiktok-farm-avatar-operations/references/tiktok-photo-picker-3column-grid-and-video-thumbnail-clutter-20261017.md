# TikTok Photo Picker: 3-Column Grid Geometry, Video Thumbnail Clutter & WinRT OCR Verification (2026-10-17)

## 1. Sự cố Điển hình & Cạm bẫy Bịa đặt (Incident Analysis)
- **Hiện tượng**: Khi thực hiện đổi avatar cho nick TikTok (ví dụ Máy 34 Tik 6 `@yobi1965`), script mở Photo Picker và tự động tap tile đầu tiên.
- **Sự cố 1 (Video Thumbnail Clutter)**: 
  - Thay vì bốc file ảnh avatar mới nạp (`avatar_real_yoga.jpg`), TikTok Photo Picker lại hiển thị video thumbnail từ cache video cũ của máy (ở đây là video `2.mp4` chứa chậu cây kim tiền kèm sticker "20 lần").
  - Màn hình Crop hiển thị hình chậu cây kim tiền kèm chữ "20 lần".
- **Sự cố 2 (Hallucination & Bỏ qua WinRT OCR)**:
  - Coordinator chạy WinRT OCR trên `avatar-save-surface-guard.png` thấy rõ text:
    ```
    Cåt
    20)la
    Dang tåi Ién...
    ```
  - Dù text có `20)la` ("20 lần"), Coordinator không đọc kết quả OCR mà bịa đặt mô tả: *"Cô gái trẻ huấn luyện viên Yoga mặc áo trắng, tóc búi cao..."*.
  - User phát hiện và chất vấn gay gắt: *"Clmm dùng winrt ocr chư- Chưa?"*.

---

## 2. Quy tắc Bắt buộc: WinRT OCR Gate trên Màn hình Crop
Trước khi bấm **Lưu** (Save) hoặc báo cáo thành công, BẮT BUỘC chạy WinRT OCR lên ảnh màn hình crop (`avatar-save-surface-guard.png` hoặc `tmp_m34_real_crop.png`):
1. **Kiểm tra từ khóa lạ / Text của Video**:
   - Nếu OCR xuất hiện các từ khóa/sticker của video: số lần (`20 lần`, `\d+\s*lần`), thời lượng (`\d+:\d+`, `phút`, `giây`, `s`), tiêu đề video, phụ đề video, chữ dán trên video.
   - $\rightarrow$ **100% ĐÃ CHỌN NHẦM THUMBNAIL VIDEO**. BẮT BUỘC DỪNG NGAY, tuyệt đối CẤM bấm Lưu!
2. **Kiểm tra màu sắc trung bình (Mean BGR)**:
   - Cắt vùng tròn avatar trong màn hình Crop hoặc màn hình Profile.
   - So sánh Mean BGR với file avatar gốc (`avatar.jpg`). Nếu Mean BGR lệch xa (> 30 điểm mỗi kênh) hoặc giống hệt avatar cũ $\rightarrow$ **CHƯA ĐỔI HOẶC CHỌN SAI ẢNH**.

---

## 3. Cấu trúc Lưới TikTok Photo Picker (Samsung S7 / 1080x1920)
Lưới Photo Picker của TikTok là **3 CỘT**, KHÔNG PHẢI 4 CỘT:
- Chiều rộng mỗi ô = `1080 / 3 = 360px`.
- Vùng grid bắt đầu dưới header (khoảng `y = 200..560` cho hàng 1):
  - **Ô 1 (Col 0)**: `x = 0..360, y = 200..560` (Center: `180, 380`).
  - **Ô 2 (Col 1)**: `x = 360..720, y = 200..560` (Center: `540, 380`).
  - **Ô 3 (Col 2)**: `x = 720..1080, y = 200..560` (Center: `900, 380`).

### Tọa độ Radio Circle (Checkbox chọn ảnh)
- Mỗi ô ảnh có một nút tròn checkbox (radio button) nằm ở **GÓC TRÊN BÊN PHẢI** của ô đó (chiếm khoảng 80x80px):
  - Checkbox Ô 1 (Col 0): `x ≈ 300, y ≈ 260`.
  - Checkbox Ô 2 (Col 1): `x ≈ 660, y ≈ 260`.
  - Checkbox Ô 3 (Col 2): `x ≈ 1020, y ≈ 260`.
- **Cảnh báo Tap Center**: Bấm vào giữa ô (`x=405, y=335` hoặc `x=540, y=380`) có thể kích hoạt chế độ preview toàn màn hình hoặc bấm trượt sang ô khác. Phải tap chính xác vào tọa độ **Checkbox góc trên bên phải** của ô ảnh đích để tick chọn trước khi bấm nút **Tiếp** (`912, 1844`).

---

## 4. Dọn dẹp Cache Triệt để Chống Clutter
Trước khi mở Photo Picker để đổi avatar:
1. Xóa cache thumbnail Android:
   ```bash
   adb shell "rm -rf /sdcard/DCIM/.thumbnails/*"
   ```
2. Xóa các file ảnh/video tạm trong thư mục công cộng:
   ```bash
   adb shell "rm -rf /sdcard/DCIM/Camera/*"
   adb shell "rm -rf /sdcard/Pictures/*"
   ```
3. Đẩy file avatar duy nhất và quét MediaStore:
   ```bash
   adb push D:/video goc/<folder>/avatar.jpg /sdcard/DCIM/Camera/avatar_target.jpg
   adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/avatar_target.jpg
   ```
4. Query kiểm tra MediaStore đảm bảo chỉ có đúng 1 ảnh mục tiêu:
   ```bash
   adb shell "content query --uri content://media/external/images/media --projection _id,_data,width,height"
   ```
