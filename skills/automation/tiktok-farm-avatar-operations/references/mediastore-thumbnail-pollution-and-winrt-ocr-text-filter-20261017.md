# MediaStore Thumbnail Pollution, Haar Cascade False Positives, and WinRT OCR Text-Sticker Detection (2026-10-17)

## 1. Bối Cảnh Sự Cố & Hiện Tượng (Incident Analysis)
- **Thiết bị & Tài khoản**: Máy 34 Slot 6 (`@yobi1965`, cụm Kibe).
- **Hiện tượng**:
  1. Trong thư mục `representative_frames`, file frame bị trích nhầm đồ vật mờ đỏ, nhưng thuật toán Haar Cascade (`haarcascade_frontalface_default.xml`) bị **false positive** nhận diện mảng màu đỏ thành khuôn mặt. Coordinator cắt ra một mảng đỏ nhòe nhoẹt không có ngũ quan người.
  2. Khi upload lên app TikTok, bộ đệm MediaStore và thư mục `/sdcard/DCIM/.thumbnails/` lưu thumbnail của video đã render trước đó (`2.mp4` - chậu cây kim tiền kèm sticker "20 lần"). Photo Picker của TikTok ưu tiên bốc tile đầu tiên từ cache/thumbnails thay vì file avatar mới.
  3. Kết quả màn hình Crop hiển thị chữ sticker `20)la` trên chậu cây, nhưng Coordinator **bỏ qua kết quả WinRT OCR** và bịa đặt mô tả: *"Cô gái trẻ huấn luyện viên Yoga mặc áo trắng..."*.
  4. User kiểm tra thực tế và chất vấn gay gắt vì hành vi gửi ảnh mù và không dùng WinRT OCR đọc chữ trên ảnh crop.

---

## 2. Các Bài Học & Quy Tắc Bắt Buộc (Invariants)

### A. Haar Cascade False-Positive Trap & Trích xuất từ Video Gốc
- **Cấm tin tưởng mù quáng vào Haar Cascade**: Haar cascade rất dễ nhận diện sai các mảng bokeh, vân đá, đệm đỏ, hoa văn thành khuôn mặt (`detectMultiScale` trả về 1 face nhưng thực tế không có người).
- **Quy trình fallback chuẩn**: Khi representative frames không rõ ràng hoặc nghi ngờ, **bắt buộc mở trực tiếp video gốc MP4** (`cv2.VideoCapture`) tại các mốc giây 1s, 2s, 3s để lấy frame có người thật, độ phân giải cao và ánh sáng chuẩn.

### B. WinRT OCR Filter: Chặn đứng Picker chọn nhầm Video Thumbnail
- **Quy tắc vàng**: Avatar cá nhân chuẩn (Yoga, đời sống, bác sĩ, làm đẹp) **TUYỆT ĐỐI KHÔNG CÓ TEXT STICKER HAY CHỮ SỐ** trên ảnh.
- **Kiểm tra OCR trước khi chấp nhận màn hình Crop**:
  - Chạy WinRT OCR (`ocr_tool.py` hoặc `ocr_boxes.ps1`) trên ảnh chụp màn hình Crop (`avatar-save-surface-guard.png`).
  - Nếu OCR xuất hiện bất kỳ từ khóa lạ hoặc text overlay dạng:
    - Số kèm đơn vị: `"20 lần"`, `"20)la"`, `"30s"`, `"10p"`, `"tap 1"`.
    - Từ khóa video: `"video"`, `"clip"`, `"thời lượng"`, `"duration"`, watermark nick.
  - $\rightarrow$ **KẾT LUẬN NGAY**: Picker đã chọn nhầm video thumbnail hoặc frame render có gắn text/sticker, KHÔNG ĐƯỢC PHÉP BẤM LƯU và KHÔNG ĐƯỢC PHÉP BÁO DONE.

### C. Triệt phá MediaStore & Thumbnail Pollution trước khi nạp Avatar
Trước khi mở TikTok đổi avatar trên bất kỳ máy Android nào:
1. **Xóa sạch thumbnails cache**:
   ```bash
   adb shell rm -rf /sdcard/DCIM/.thumbnails
   ```
2. **Dọn sạch ảnh cũ trong Camera và Pictures**:
   ```bash
   adb shell rm -rf /sdcard/DCIM/Camera/*
   adb shell rm -rf /sdcard/Pictures/*
   ```
3. **Đẩy file avatar duy nhất vào `/sdcard/DCIM/Camera/avatar_target.jpg`**:
   ```bash
   adb push <local_avatar.jpg> /sdcard/DCIM/Camera/avatar_target.jpg
   adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/avatar_target.jpg
   ```
4. **Xác thực MediaStore chỉ có duy nhất 1 ảnh**:
   ```bash
   adb shell content query --uri content://media/external/images/media
   ```
   Chỉ khi kết quả trả về đúng 1 dòng trỏ về `avatar_target.jpg`, mới khởi động app TikTok để vào picker.
