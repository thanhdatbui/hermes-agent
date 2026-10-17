# Photo Picker Video Tile Trap & WinRT OCR Verification Discipline (2026-10-17)

## Bối cảnh & Hiện tượng (Critical Failure Analysis)
Khi thực hiện quy trình nạp hoặc đổi avatar cho tài khoản TikTok trên máy farm Android (Samsung S7 / TikTok v47+):
1. **Photo Picker Video Thumbnail Collision (Bẫy chọn nhầm Thumbnail Video cũ)**:
   - Photo Picker của app TikTok hiển thị các media gần đây dựa trên cơ chế cache nội bộ của app kết hợp MediaStore.
   - Khi runner tự động nạp avatar mới và mở picker, **tile đầu tiên** (ở vị trí `(0, 0)` hoặc hàng 1, cột 1) có thể KHÔNG phải là ảnh avatar vừa push, mà là thumbnail của video vừa đăng gần nhất (ví dụ video render chứa sticker chữ "20 lần", cây cảnh, thumbnail chữ...).
   - Kết quả: App chọn nhầm thumbnail video làm avatar. Khi vào màn hình Crop (`CropActivity`), vòng tròn crop hiển thị một góc của video cũ (chậu cây, mảng màu đỏ, sticker chữ...).
2. **Ảo giác nghiêm trọng (Hallucination & Fake Visual Report)**:
   - Agent nhìn lướt hoặc không chạy WinRT OCR trên ảnh màn hình Crop / Save (`avatar-save-surface-guard.png`).
   - Mặc dù OCR thực tế đọc ra các từ khóa của thumbnail video cũ (ví dụ: `20)la`, `20 lần`, `clip`, `video`), agent vẫn tưởng tượng và miêu tả sai sự thật rằng ảnh hiển thị đúng đối tượng mục tiêu (ví dụ: "cô gái tập yoga áo trắng").
   - Điều này vi phạm trực tiếp Invariant **CẤM GỬI ĐỐI PHÓ / GỬI ẢNH MÙ**.

---

## Quy trình Kiểm chuẩn Bắt buộc (Strict Invariant Workflow)

### 1. Bắt buộc dùng WinRT OCR đọc mọi ký tự trên màn hình Crop
Trước khi báo cáo hoặc gửi bất kỳ ảnh crop/avatar nào (`MEDIA:`):
- **BẮT BUỘC** chạy WinRT OCR (`python D:/Taadaa/tools/ocr_tool.py <screenshot_path>` hoặc qua `ocr_boxes.ps1`).
- **Từ khóa cấm xuất hiện trên màn hình Crop avatar:**
  - Nếu OCR phát hiện các từ lạ liên quan đến nội dung video cũ (ví dụ: số lần, tên video, sticker chữ, tiêu đề clip như `20 lần`, `20)la`, `video`, `clip`, `phút`, `giây`...): **100% ĐÃ CHỌN NHẦM THUMBNAIL VIDEO**.
  - **CẤM TUYỆT ĐỐI** bấm Lưu hoặc báo cáo thành công khi màn hình crop chứa các text lạ này.

### 2. Xác thực vị trí Tile trong Photo Picker (Inspect Grid)
Nếu picker bị kẹt thumbnail video cũ ở tile 1:
- Không tap mù vào tile 1 (`215, 276` hoặc `140, 360`).
- Cắt các tile trong Photo Picker (`tmp_tile_0_0.jpg`, `tmp_tile_0_1.jpg`...) và đối soát:
  - So sánh Mean BGR hoặc kiểm tra trực quan qua vision để tìm đúng tile chứa file ảnh avatar vừa nạp (ví dụ tile 2 tại `(405, 335)`).
  - Tap chính xác vào đúng tọa độ của tile chứa ảnh thật trước khi bấm "Tiếp".

### 3. Dọn dẹp cache MediaStore & Thumbnail triệt để
Trước khi nạp avatar mới, bắt buộc:
1. Xóa sạch cache thumbnail:
   ```bash
   adb shell rm -rf /sdcard/DCIM/.thumbnails/*
   ```
2. Dọn sạch ảnh rác trong `/sdcard/DCIM/Camera/*` và `/sdcard/Pictures/*`.
3. Push duy nhất 1 file avatar mục tiêu vào `/sdcard/DCIM/Camera/avatar_yoga.jpg`.
4. Phát broadcast MediaScanner và kiểm tra `content query --uri content://media/external/images/media` chỉ trả về đúng 1 row duy nhất.
