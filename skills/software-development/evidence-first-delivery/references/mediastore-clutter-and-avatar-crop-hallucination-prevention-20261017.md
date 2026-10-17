# Anti-Hallucination & Anti-Stale MediaStore Clutter in Avatar Crop (2026-10-17)

## 1. Bản Chất Sự Cố & Bẫy Ảo Giác Thị Giác (Visual Hallucination Trap)
Trong phiên chuẩn hoá avatar trên máy farm Android (`Máy 34` / `@yobi1965`):
- **Hiện tượng sự cố**: Agent trích xuất ảnh khuôn mặt người tập Yoga và lưu vào `avatar.jpg`, sau đó chạy batch runner nạp lên máy và thu được ảnh chụp màn hình `avatar-save-surface-guard.png`. Agent đã báo cáo "thành công" kèm mô tả chi tiết: *"ảnh khuôn mặt người phụ nữ ngồi thẳng yoga, mắt nhìn thẳng, phía dưới có nút Lưu màu đỏ"*.
- **Thực tế người dùng nhận được**: Màn hình cắt ảnh thực tế trên điện thoại hiển thị **một vật màu hồng/mũ bảo hiểm trước hàng rào** chứ hoàn toàn không có người phụ nữ nào! Người dùng đã phản ứng gay gắt về việc agent mô tả sai sự thật và chọn ảnh rác.

## 2. Gốc Rễ Kỹ Thuật (Technical Root Causes)
1. **MediaStore Clutter & Stale Photo Picker Index**:
   - Khi runner tự động nạp file ảnh avatar vào thiết bị (`/sdcard/Pictures/` hoặc `/sdcard/DCIM/Camera/`), hệ thống MediaStore của Android có thể chưa kịp quét (`MEDIA_SCANNER_SCAN_FILE`) hoặc Photo Picker của TikTok sắp xếp theo tiêu chí khác (cache thư viện cũ, album Zalo/Facebook/Screenshots).
   - Tọa độ tap ô đầu tiên trong gallery (`input tap 225 255` hoặc tile 1) bị chọn trúng **ảnh rác cũ lưu cữu từ trước** (ảnh mũ bảo hiểm/vật màu hồng) thay vì ảnh avatar vừa nạp.
2. **Ảo giác xác nhận (Confirmation Bias / Hallucination)**:
   - Agent biết trước mình vừa nạp file `avatar_candidate2.jpg` (ảnh cô gái tập Yoga), nên khi nhìn thấy màn hình Crop có viền tròn và nút Lưu đỏ, agent đã ngộ nhận và mô tả dựa trên **kỳ vọng chủ quan** thay vì **đọc thực tế điểm ảnh qua OCR / Vision**.
   - Agent không đối soát Mean BGR / HSV hoặc so sánh độ tương đồng histogram giữa ảnh crop trên màn hình với file `avatar.jpg` gốc.

## 3. Quy Trình Vận Hành & Khắc Phục Bắt Buộc (Invariant Protocol)

### Bước 1: Dọn sạch MediaStore & Cách ly thư viện trước khi nạp ảnh
Trước khi nạp bất kỳ file avatar mới nào lên thiết bị:
1. Xóa toàn bộ ảnh trong thư mục tạm và dọn index MediaStore:
   ```bash
   adb shell "rm -f /sdcard/DCIM/Camera/av_* /sdcard/Pictures/av_*"
   adb shell "content delete --uri content://media/external/images/media --where \"_data LIKE '%/av_%' OR _data LIKE '%/avatar%'\""
   ```
2. Đẩy file ảnh mới với timestamp duy nhất và quét index tường minh:
   ```bash
   TS=$(date +%s)
   adb push "D:/TIKTOK-videonuoinick/<folder>/avatar.jpg" "/sdcard/DCIM/Camera/av_target_${TS}.jpg"
   adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file:///sdcard/DCIM/Camera/av_target_${TS}.jpg"
   ```
3. Query kiểm tra MediaStore đảm bảo file mới nhất đứng đầu bảng:
   ```bash
   adb shell "content query --uri content://media/external/images/media --projection _id,_data,date_added --sort 'date_added DESC' | head -n 2"
   ```

### Bước 2: Soi mắt kiểm tra thực tế (Anti-Hallucination Verification Gate)
- **CẤM TUYỆT ĐỐI mô tả theo kỳ vọng**:
  - Phải crop chính xác vùng tròn của màn hình crop (`[140, 480, 940, 1280]`) và phân tích điểm ảnh thực tế.
  - So sánh Mean BGR giữa vùng tròn trên màn hình crop với file `avatar.jpg` gốc:
    $$\Delta BGR = \frac{1}{3} \sum (|B_1 - B_2| + |G_1 - G_2| + |R_1 - R_2|)$$
  - Nếu $\Delta BGR > 25.0$, **BẮT BUỘC KẾT LUẬN LÀ CHỌN SAI ẢNH** (Photo Picker chọn nhầm ảnh rác/ảnh cũ). DỪNG NGAY không được bấm Lưu!
- **Kiểm tra phát hiện khuôn mặt trên màn hình crop**:
  - Dùng OpenCV Haar Cascade hoặc WinRT OCR chạy trực tiếp trên vùng crop: Nếu không phát hiện được khuôn mặt người (`len(faces) == 0`) hoặc màu sắc chủ đạo là vật thể lạ (như vật màu hồng/đen), cấm gửi ảnh báo DONE.
