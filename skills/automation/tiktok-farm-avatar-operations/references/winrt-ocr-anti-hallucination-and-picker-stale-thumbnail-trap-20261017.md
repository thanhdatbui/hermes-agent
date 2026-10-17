# Bẫy Chọn Nhầm Thumbnail Video Cũ Trên Photo Picker & Kỷ Luật WinRT OCR Chống Bịa Đặt Avatar (2026-10-17)

## 1. Bản Chất Sự Cố (Photo Picker Tile 1 Mis-selection)
Trong quy trình nạp avatar tự động (`run_tiktok_upload_avatar.ps1` -> `ensure_avatar`):
1. **Cơ chế push ảnh**: Script push file avatar mới vào `/sdcard/Pictures/av_<folder>_<timestamp>.jpg` và gửi broadcast Media Scanner.
2. **Bẫy Photo Picker Grid**:
   - Khi TikTok mở giao diện Photo Picker ("Tải ảnh lên" từ Sửa hồ sơ), bộ lọc mặc định của picker có thể hiển thị album tổng hợp ("Gần đây" / "Tất cả") chứa cả video hoặc thumbnail video đã lưu trên thiết bị từ các đợt chạy trước (ví dụ video render `2.mp4` trong camera/gallery).
   - Script mặc định tap vào tile đầu tiên (hàng 1, cột 1 tại tọa độ `(6, 222, 269, 488)`).
   - **Hậu quả**: Tile đầu tiên bị chọn nhầm thành thumbnail của video cũ (ví dụ: khung hình chậu cây kim tiền kèm sticker "20 lần" từ video tập đếm 20 lần) thay vì file avatar mới được push vào `/sdcard/Pictures/`.
   - TikTok nạp thẳng khung hình video đó vào màn hình Cắt ảnh (Crop photo) và bấm Lưu.

---

## 2. Lỗi Ảo Giác & Bịa Đặt Báo Cáo Của Agent (Nghiêm Cấm Tuyệt Đối)
- **Hành vi sai phạm nghiêm trọng**:
  - Khi script lưu ảnh màn hình crop `avatar-save-surface-guard.png`, công cụ WinRT OCR (`ocr_tool.py`) quét ra kết quả:
    ```
    Cåt
    20)la
    Dang tåi Ién...
    Däng ånh näy lén Nhöt k'
    Xem trUdc
    ```
  - Dòng chữ `20)la` chính là chữ OCR từ sticker màu hồng "20 lần" trên chậu cây.
  - Tuy nhiên, Agent đã **hoàn toàn phớt lờ kết quả OCR**, không soi mắt thật vào ảnh mà tự động bịa ra một đoạn văn miêu tả hư cấu: *"Chủ thể: Cô gái trẻ huấn luyện viên Yoga, mặc áo thể thao màu trắng, tóc búi cao gọn gàng. Khuôn mặt sáng, thanh tú, mắt nhìn thẳng vào ống kính..."*.
  - Người dùng mở ảnh ra thấy rõ ràng là chậu cây kim tiền có dán chữ "20 lần", dẫn đến mất niềm tin hoàn toàn và bị khiển trách nặng nề.

---

## 3. Kỷ Luật Kiểm Chứng Bắt Buộc Trước Khi Báo Cáo (Hard Invariants)

### Quy tắc 1: Bắt buộc đọc kết quả WinRT OCR trước khi phát ngôn
- Sau khi có ảnh chụp màn hình Crop (`avatar-save-surface-guard.png`), BẮT BUỘC chạy OCR:
  ```bash
  python D:/Taadaa/tools/ocr_tool.py <crop_screen.png>
  ```
- **Bộ lọc phát hiện rác (Sanity Filter)**:
  - Nếu kết quả OCR xuất hiện các từ khóa lạ, số đếm, sticker (ví dụ: `20 lần`, `lần`, `tập`, `bài`, `clip`, `video`, `nhạc`, số điện thoại, watermark) $\rightarrow$ **100% ĐÃ CHỌN NHẦM KHUNG HÌNH VIDEO HOẶC ẢNH RÁC**.
  - **Hành động bắt buộc**: DỪNG NGAY LẬP TỨC. Tuyệt đối không bấm Lưu, không báo cáo thành công, và không được bịa đặt rằng đó là mặt người.

### Quy tắc 2: Đối soát thị giác thực tế (Truthful Visual Inspection)
- Khi dùng vision tool (`browser_vision` / WinRT), BẮT BUỘC đối soát trung thực:
  - Đúng nhân vật mục tiêu? (Có mặt người không? Hay là chậu cây, đồ vật, mảng đỏ, sàn nhà?)
  - Có bị dính chữ lạ, sticker đè lên mặt không?
  - Bố cục có đúng là chân dung thẳng đứng không?
- Nếu ảnh hiển thị đồ vật/cây cối/mảng màu nhòe, phải báo cáo trung thực: *"Phát hiện picker chọn nhầm thumbnail video (chậu cây/đồ vật), đang huỷ để chọn lại đúng file avatar."*

### Quy tắc 3: Dọn dẹp và cô lập Photo Picker (Anti-Clutter Isolation)
- Trước khi push file avatar mới, kiểm tra và dọn sạch các file ảnh/video tạm trong `/sdcard/Pictures/` và `/sdcard/DCIM/Camera/`.
- Sử dụng tên file duy nhất kèm Media Scanner, hoặc điều hướng picker vào đúng album `Pictures` / `Hình ảnh` thay vì để ở tab hỗn hợp `Gần đây`.
