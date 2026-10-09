# TikTok 47.x Profile Avatar Edit: Bút Chì Góc Trái & Né Bẫy Màn Story (2026-09-24)

## Bối Cảnh
Trên các thiết bị Samsung S7 (1080x1920) chạy TikTok v47.x, giao diện Profile cá nhân có sự thay đổi lớn:
1. Nút chữ "Sửa hồ sơ" truyền thống biến mất khỏi phần thân Profile.
2. Nút Bút Chì xuất hiện ở góc trên bên trái header Profile (`bounds=[24,96][126,204]`, tâm `(75, 150)`).
3. Bấm vào vòng tròn Avatar chính giữa Profile sẽ mở ra màn hình **"Thêm vào Nhật ký"** (Story Picker). Nếu chọn ảnh và lưu ở màn này, ảnh sẽ được đăng lên **Story 24h** thay vì đổi avatar trang cá nhân.

## Quy Trình Tự Động Đổi Avatar Chuẩn TikTok 47.x
1. **Mở Sửa hồ sơ**:
   - Tap vào nút Bút Chì góc trên bên trái: `(75, 150)`.
   - Chờ màn hình Sửa hồ sơ (`HeaderDetailEditActivity`) sẵn sàng.
2. **Mở bộ chọn ảnh**:
   - Tap vào ảnh đại diện "Thay đổi ảnh": `(540, 400)`.
   - Chọn "Tải ảnh lên" từ bottom sheet: `(400, 1570)`.
3. **Chọn và Cắt ảnh**:
   - Chọn ảnh đầu tiên trong picker: `(137, 355)`.
   - Bấm "Tiếp": `(912, 1842)`.
   - Tại màn hình xác nhận: bấm "Tiếp (1)": `(912, 1842)` để vào màn hình Cắt (Crop).
4. **Lưu Avatar**:
   - Đảm bảo checkbox "Đăng ảnh này lên Nhật ký" (`checked=false`).
   - Bấm "Lưu": `(792, 1794)`.
   - Nhấn phím Back (`KEYCODE_BACK`) để quay về trang Profile.
   - Chụp ảnh màn hình nghiệm thu visual avatar mới xuất hiện trên Profile.
