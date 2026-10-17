# Invariant Bắt Buộc OCR Rà Soát Text/Sticker Đè & Gửi Ảnh Kiểm Chứng Tức Thì (2026-10-17)

## 1. Sự Cố Thực Tế
Trong phiên đổi avatar cho nick `@yobi1965` (Folder 434), Coordinator đã gặp phải các lỗi nghiêm trọng sau:
1. **Ảo giác miêu tả & Không chạy WinRT OCR**: Trích xuất frame từ video `2.mp4` bị dính sticker bài tập màu hồng có chữ `"20 lần/ngày"`. Coordinator không chạy `ocr_tool.py` mà chỉ nhìn lướt qua vision, tự huyễn hoặc thành *"cô gái tập yoga mặc áo trắng hai tay đưa lên"* và gửi đi. Kết quả bị User bắt quả tang ảnh có chữ `"20 lần/"` và chậu cây kim tiền.
2. **Không gửi ảnh cho User kiểm tra ngay lập tức**: Khi gen ảnh xong hoặc chụp được ảnh kiểm chứng trên màn hình Crop, Agent ôm việc chạy tiếp một chuỗi hành động ngầm mà không gửi ảnh `MEDIA:` để User duyệt trước.
3. **Ảo giác trạng thái upload thành công**: Script chạy trả về `exit=0` do màn hình Crop đóng lại, nhưng thực tế app TikTok bị rớt request upload ngầm (`api.tiktokv.com`), avatar trên hồ sơ vẫn là ảnh phong cảnh sa mạc/đồi núi cũ. Agent lại miêu tả là *"đã đổi thành công sang ảnh cô gái yoga"*.

## 2. Invariant Kỷ Luật Thao Tác (Bắt Buộc 100%)

### Quy Tắc 1: WinRT OCR Rà Soát Text/Sticker Trên Ảnh Crop (Cấm Chữ Rác)
Trước khi lưu bất kỳ ảnh nào làm `avatar.jpg` hoặc gửi preview cho User:
- BẮT BUỘC chạy `python D:/Taadaa/tools/ocr_tool.py <image_path>`.
- Nếu kết quả OCR phát hiện bất kỳ chữ nào liên quan đến bài tập, watermark, sticker (ví dụ: `20`, `lần`, `ngày`, `phút`, `yoga`, `@`, số điện thoại, ngày tháng):
  - **TUYỆT ĐỐI CẤM SỬ DỤNG** làm avatar.
  - Phải điều chỉnh lại bounding box crop để loại bỏ hoàn toàn vùng text, hoặc đổi sang video gốc khác sạch text (như video hướng dẫn không chèn sticker).
  - Chỉ chấp nhận ảnh khi OCR trả về rỗng (hoặc chỉ có ngũ quan tự nhiên).

### Quy Tắc 2: Tạo Xong Ảnh/Preview Là Bắt Buộc Gửi `MEDIA:` Ngay Cho User
- Khi User yêu cầu *"Đổi ava"* hoặc *"Đổi ảnh khác"*:
  - Sau khi trích xuất và tạo file preview tròn (`tmp_circle_candidate_clean.jpg`), **BẮT BUỘC gửi ngay thẻ `MEDIA:<path>` trong câu trả lời tiếp theo**.
  - **CẤM TUYỆT ĐỐI** tự ý chạy tiếp chuỗi nạp lên thiết bị trong bóng tối khi User chưa được nhìn thấy hình ảnh mới.
  - Phải gửi ảnh kèm xác nhận ngắn gọn: đã qua OCR sạch chữ và soi mắt bằng vision.

### Quy Tắc 3: Đối Soát Thực Tế Tại Vòng Tròn Profile (Anti-False-Positive)
- Sau khi bấm "Lưu", CẤM tin vào `exit=0` hay màn hình Crop đóng lại.
- BẮT BUỘC chụp lại màn hình Hồ sơ chính (`Profile`), crop đúng vùng avatar `[756, 324][1044, 612]`, đo Mean BGR và soi mắt bằng `browser_vision`:
  - Nếu Mean BGR vẫn trùng với avatar cũ -> Upload đã thất bại (rớt socket proxy), BẮT BUỘC báo cáo trung thực, cấm bịa đặt là đã đổi thành công.
