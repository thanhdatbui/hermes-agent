# Gallery Picker Screenshot Trap & Right-Side Avatar Upload Protocol

## 1. Bẫy Gallery Picker Đẩy Screenshot Mới Lên Đầu (False AVATAR_SMOKE_SUCCESS)
- **Căn nguyên**:
  - `run_tiktok_upload_avatar.ps1` và `state_machine.py` có logic mặc định:
    `[ENSURE_AVATAR] Tap tile ảnh đầu tiên (mới nhất sau push): (6, 222, 269, 488)`.
  - Trên Android (Samsung S7), Gallery / DocumentsUI sắp xếp theo ngày chụp hoặc media scan.
  - Các screenshot chụp màn hình Profile trước đó để phân loại layout thường nằm ở vị trí đầu tiên (Hàng 1, Cột 1).
  - Khi runner tap mù vào ô (0, 0), nó vô tình chọn lại **chính ảnh chụp màn hình chứa avatar cũ** (ví dụ ảnh nữ MC cũ), cắt và tải lên, rồi kết luận `AVATAR_SMOKE_SUCCESS` (báo cáo láo / false positive).
- **Quy trình khắc phục triệt để**:
  1. Dọn dẹp sạch file ảnh tạm trên thiết bị trước khi push:
     `rm -f /sdcard/DCIM/Camera/avatar_*.jpg /sdcard/Pictures/av_*.jpg /sdcard/Pictures/avatar_*.jpg`
  2. Push file avatar chuẩn vào `/sdcard/DCIM/Camera/IMG_<timestamp>.jpg` và bắn broadcast `MEDIA_SCANNER_SCAN_FILE`.
  3. Mở Gallery Picker, chụp màn hình và dùng OCR / Vision xác định chính xác toạ độ ô ảnh mục tiêu (ví dụ Hàng 3 Cột 4 `(943, 899)`, nút tròn `(1020, 820)`) thay vì tap mù (0, 0).
  4. Bấm `Tiếp (1)` tại `(921, 1843)`, vào màn hình `Cắt` (Crop), tap nút `Lưu` màu đỏ tại `(792, 1794)`.
  5. Đợi tối thiểu 8–10 giây cho request CDN hoàn tất, quay lại Profile, vuốt nhẹ kéo xuống để refresh trang cá nhân.
  6. **BẮT BUỘC NGHIỆM THU BẰNG VISUAL DIFF**: Chụp màn hình Profile thật, cắt vùng avatar và kiểm tra độ tương đồng với avatar nguồn. TUYỆT ĐỐI không tin vào `exit=0` hay `verified=True` của runner.

## 2. Bẫy Bố Cục Avatar Nằm Bên Phải (Right-Side Avatar Layout)
- **Đặc điểm nhận diện**:
  - Tên hiển thị nằm bên trái (`(36, 291)`), Handle `@username` ở `(38, 377)`.
  - Vòng tròn Avatar nằm ở góc trên bên phải (`x ≈ 900, y ≈ 350..470`).
  - Phía trên đỉnh Avatar có bong bóng trạng thái (Status/Note: *"Tám chuyện..."*, *"Trà hay cà phê?"*).
  - Góc dưới bên phải Avatar có icon tròn màu xanh cyan dấu cộng `+` (nút thêm Story / camera liveness).
- **Cấm kỵ**:
  - CẤM tap vào nút `+` góc dưới phải avatar (`(1002, 375)`): Sẽ kích hoạt camera Story hoặc màn hình đen quét khuôn mặt (*"Đảm bảo khuôn mặt bạn nằm gọn trong khung hình"*).
  - CẤM tap vào nửa trên của avatar nơi bong bóng ghi chú đè lên (`y < 210` trên header): Sẽ mở màn hình soạn ghi chú / story note.
- **Cách vào Sửa hồ sơ**:
  - Tap vào biểu tượng cây bút chì ở góc trên bên trái header tại `(75, 150)` (`bounds [24, 96][126, 204]`).
  - Khi màn hình Sửa hồ sơ (`EDIT_PROFILE`) mở ra: Tap nút `Thay đổi ảnh` tại `(539, 579)` để bung bottom sheet chọn `Tải ảnh lên` (`224, 1637`).
