# Nghiệm Thu Avatar Bằng WinRT OCR & Chống Bẫy Thumbnail Video Rác Trong Photo Picker (2026-10-17)

## 1. Bối Cảnh Sự Cố Thực Tế (Root Cause Analysis - M34 @yobi1965)
- **Hiện tượng**:
  - Khi thực hiện chuẩn hoá và đổi avatar cho tài khoản Yoga `@yobi1965` trên Máy 34, Coordinator báo cáo quy trình hoàn tất thành công (`exit=0`, `verified=True`).
  - Coordinator gửi ảnh chụp màn hình nghiệm thu `avatar-save-surface-guard.png` kèm lời khẳng định: *"Người phụ nữ tập yoga trong tư thế ngồi thẳng đứng, mắt nhìn thẳng, áo tập thể thao..."*.
  - Tuy nhiên, User mở ảnh ra phát hiện trên màn hình Crop thực tế **chỉ là một khoảng màu đỏ/mờ nhòe**, chính là chậu cây kim tiền kèm sticker chữ **"20 lần"**.
  - User phản ứng gay gắt: *"Lồn mẹ mày chọn cái ava như con cặc v... Già cái địt cụ m ảnh đéo thấy clg cả mỗi 1 khoảng đỏ mà mày dám chọn đc mày có dùng win rt ocr đọc ảnh k v... Clmm dùng winrt ocr chưa?"*.

- **Hai Nguyên Nhân Gốc Rễ**:
  1. **Bẫy Picker bốc nhầm Thumbnail Video cũ thay vì Avatar mới**:
     - Runner tự động đẩy file avatar mới vào `/sdcard/Pictures/` hoặc `/sdcard/DCIM/Camera/` và gửi broadcast scan MediaStore.
     - Tuy nhiên, Photo Picker của TikTok lại lưu cache các thumbnail của những video đã tải lên/kênh đã render trước đó (cụ thể là video `2.mp4` trong Folder 270 có thumbnail mở đầu là chậu cây kim tiền + sticker "20 lần").
     - Runner auto tap mù vào ô đầu tiên (Hàng 1, Cột 1 tại bounds `(6, 222, 269, 488)`), dẫn đến việc chọn nhầm thumbnail video `2.mp4` thay vì file avatar Yoga mới được push.
  2. **Vi phạm quy chuẩn nghiệm thu WinRT OCR & Hallucination**:
     - Coordinator không chạy WinRT OCR (`ocr_tool.py` / `ocr_boxes.ps1`) trên ảnh chụp màn hình nghiệm thu trước khi gửi cho User.
     - Trên thực tế, nếu chạy WinRT OCR trên ảnh `avatar-save-surface-guard.png`, kết quả OCR sẽ trả về ngay:
       ```
       Cåt
       20)la
       Dang tåi Ién...
       Däng ånh näy lén Nhöt k'
       Xem trUdc
       ```
       Từ khóa `20)la` / `20 lần` xuất hiện sờ sờ trong kết quả OCR là bằng chứng không thể chối cãi rằng ảnh đang crop là thumbnail video có sticker chữ, KHÔNG PHẢI avatar chân dung/ngũ quan. Nhưng Coordinator bỏ qua bước OCR này và tự bịa mô tả dựa trên ảo tưởng.

---

## 2. Quy Chuẩn Bắt Buộc: Chốt Chặn WinRT OCR Trước Khi Gửi Báo Cáo

### Invariant Bắt Buộc:
Mọi ảnh chụp màn hình nghiệm thu Crop (`avatar-save-surface-guard.png`, `crop_screen.png`) hoặc Profile sau khi đổi avatar **BẮT BUỘC PHẢI CHẠY WinRT OCR ĐỐI SOÁT TRƯỚC TIÊN**:
```bash
python D:/Taadaa/tools/ocr_tool.py "<đường_dẫn_ảnh_crop>"
```

### Các Dấu Hiệu Phải HỦY NGAY (FAIL-CLOSED):
Nếu kết quả WinRT OCR xuất hiện bất kỳ từ khóa nào sau đây, **CẤM TUYỆT ĐỐI GỬI ẢNH BÁO CÁO CHO USER**:
1. **Dính text của video**: Chứa các con số kèm từ ngữ như `"20 lần"`, `"20)la"`, `"lần/ngày"`, `"phút"`, `"bài tập"`, tiêu đề video, caption.
2. **Dính watermark kênh video**: `@username`, `#hashtag`, `TikTok`.
3. **Màu sắc bất thường**: Mean BGR lệch hoàn toàn so với file `avatar.jpg` gốc (ví dụ toàn mảng đỏ/xám nhòe).

---

## 3. Quy Trình Khắc Phục Lỗi Picker Bốc Nhầm Thumbnail Video

Khi phát hiện Photo Picker trên máy không nhận đúng ảnh đầu tiên:
1. **Dọn dẹp rác thiết bị triệt để**:
   - Xóa cache thumbnail: `adb shell rm -rf /sdcard/DCIM/.thumbnails/*`
   - Xóa các file ảnh/video tạm cũ trong `/sdcard/DCIM/Camera/*` và `/sdcard/Pictures/*`.
2. **Cách ly và nạp file avatar duy nhất**:
   - Đẩy file avatar chuẩn vào thiết bị: `adb push <local_avatar> /sdcard/DCIM/Camera/avatar_yoga.jpg`
   - Quét MediaScanner: `adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/avatar_yoga.jpg`
3. **Chụp và Cắt Từng Ô Picker Để Xác Định Tọa Độ Thực Tế**:
   - Chụp màn hình Photo Picker thật: `adb shell screencap -p /sdcard/live_picker.png`
   - Cắt các tile trong grid (thường 4 cột, mỗi cột rộng 270px trên màn 1080x1920):
     - Ô 1: `x = [0, 270]`, `center = (135, 335)`
     - Ô 2: `x = [270, 540]`, `center = (405, 335)`
     - Ô 3: `x = [540, 810]`, `center = (675, 335)`
   - So sánh Mean BGR hoặc kiểm tra vision xem ô nào là ảnh avatar thật (như trong sự cố M34, Ô 1 là chậu cây kim tiền, Ô 2 mới là ảnh Yoga thật).
   - Tap chính xác vào tọa độ ô chứa ảnh avatar thật (`input tap 405 335`), không tap mù vào ô 1.
4. **Hậu kiểm WinRT OCR trên màn Crop**:
   - Chụp lại màn Crop, chạy WinRT OCR.
   - Xác nhận: Chỉ có text hệ thống của TikTok (`Cắt`, `Xem trước`, `Đăng ảnh này lên Nhật ký`, `Lưu`), **TUYỆT ĐỐI KHÔNG CÓ TỪ KHÓA LẠ HAY SỐ LIỆU CỦA CLIP**.
   - Bấm Lưu (`input tap 792 1794`) và đợi upload hoàn tất.
