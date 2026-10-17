# TikTok Photo Picker 3-Column Grid, Radio Checkbox Coordinates, and Immediate Delivery Invariant (2026-10-17)

## 1. Bối cảnh & Hiện tượng (The Video Thumbnail Clutter Trap)
Trong quá trình nạp avatar tự động trên thiết bị Android farm (TikTok v47+), sau khi dọn sạch thư mục `/sdcard/DCIM/Camera` và `/sdcard/Pictures` và push file avatar mới (`avatar_yoga.jpg`), Photo Picker của TikTok vẫn có thể hiển thị một video thumbnail ở ô đầu tiên:
- Mặc định Photo Picker mở album **"Gần đây" (Recent)** — album này tổng hợp cả ảnh tĩnh lẫn video clip đã đăng gần nhất hoặc cache nội bộ của app TikTok.
- Nếu chọn mù ô đầu tiên (`Tile 1`), app sẽ chọn nhầm thumbnail của video (ví dụ: khung hình đầu của clip chứa chậu cây, chữ sticker "20 lần/ngày", hình mờ đỏ) thay vì file avatar ảnh tĩnh mới nạp.

---

## 2. Cấu trúc Lưới Photo Picker (1080x1920) & Tọa độ Radio Checkbox
Photo Picker trên màn hình Samsung 1080x1920 được chia thành **lưới 3 cột** (mỗi cột rộng 360px), bắt đầu từ dưới thanh header "Gần đây" (khoảng `y = 200`):
- **Cột 0 (Tile 1)**: `x = 0..360`, `y = 200..560`.
- **Cột 1 (Tile 2)**: `x = 360..720`, `y = 200..560`.
- **Cột 2 (Tile 3)**: `x = 720..1080`, `y = 200..560`.

### Cạm bẫy Tọa độ Tap (Tap Center vs Radio Checkbox):
- Tap vào giữa ô (ví dụ `x = 405, y = 335`) có thể bị TikTok tính là mở xem trước (preview) hoặc chạm trượt, không kích hoạt chọn ảnh.
- Nút tròn chọn ảnh (circle checkbox) nằm ở **GÓC TRÊN BÊN PHẢI** của mỗi ô:
  * **Checkbox Tile 1 (Cột 0)**: `(x = 300, y = 260)`
  * **Checkbox Tile 2 (Cột 1 - Thường là avatar ảnh tĩnh nếu Tile 1 là video)**: `(x = 660, y = 260)`
  * **Checkbox Tile 3 (Cột 2)**: `(x = 1020, y = 260)`
- Nút **Tiếp (Next)** nằm ở góc dưới bên phải: `(x = 912, y = 1844)` hoặc khoảng `(860..960, 1820..1870)`.
- Nút **Lưu (Save)** trên màn hình Crop: `(x = 792, y = 1794)`.

---

## 3. Quy tắc WinRT OCR Bắt buộc Trên Màn hình Crop (Chống Chọn Nhầm Video)
Trước khi bấm Lưu hoặc báo cáo hoàn thành:
1. Chụp màn hình Crop (`screencap -p`).
2. Chạy WinRT OCR (`ocr_tool.py` hoặc `ocr_boxes.ps1`).
3. **Blacklist Từ khóa Video / Rác**:
   - Nếu OCR phát hiện các chuỗi text lạ như `"20 lần"`, `"lần/ngày"`, `"clip"`, `"video"`, thời lượng (ví dụ `0:15`, `0:30`), hoặc tiêu đề trình duyệt web $\rightarrow$ **CẤM BẤM LƯU**.
   - Đây là dấu hiệu chắc chắn picker đang chọn nhầm video thumbnail.
4. **Giải pháp xử lý khi Tile 1 bị chiếm bởi video**:
   - Tap vào nút dropdown album "Gần đây" tại `(x = 556, y = 144)` $\rightarrow$ chọn album **"Hình ảnh"** (Pictures/Ảnh) để lọc sạch video.
   - HOẶC tap trực tiếp vào checkbox của Tile 2 tại `(x = 660, y = 260)` nơi chứa file ảnh avatar mới.

---

## 4. Kỷ luật Phản hồi Trực quan Ngay Lập Tức (Immediate Media Delivery Invariant)
- **Sự cố thực tế**: Khi chụp được ảnh màn hình Sửa hồ sơ với avatar mới, Agent tiếp tục chạy ngầm lệnh Back để chụp tiếp trang Profile chính mà không gửi ảnh Sửa hồ sơ đã có cho User, khiến User phải giục: *"sao mày đéo gửi ảnh đẻ t kiểm tra luôn"*.
- **Quy tắc BẮT BUỘC**:
  1. Khi đã kéo được ảnh chụp màn hình quan trọng (Crop screen, Sửa hồ sơ với avatar mới) về máy, BẮT BUỘC phải đính kèm thẻ `MEDIA:<path>` ngay trong tin nhắn phản hồi tiếp theo.
  2. CẤM TUYỆT ĐỐI ôm giữ ảnh trong máy để chạy tiếp các subagents khác mà không cho User xem ảnh hiện trường đang có.
