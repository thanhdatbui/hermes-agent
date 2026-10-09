# Kỷ luật Crop Cận Cảnh Bằng Chứng UI & Chống Ảo Giác Ảnh Mù Toàn Màn Hình (08/10/2026)

## 1. Hiện tượng & Sự cố thực tế (Incident 08/10/2026)
- **Bối cảnh:** Khi điều tra lỗi nhập mã giới thiệu Phygitals trên máy thật (Samsung Galaxy S7, độ phân giải 1080x1920). Server backend trả về thông báo lỗi nhỏ nằm ngay dưới nút Apply: *"We couldn't verify your code right now — it's saved and we'll retry automatically."*
- **Sai lầm:** Agent chụp ảnh toàn màn hình dọc 1080x1920 và gửi nguyên ảnh này qua Telegram. Khi hiển thị trên Telegram (cả điện thoại lẫn desktop), ảnh dọc bị co tỷ lệ thu nhỏ (downscale) khiến dòng thông báo lỗi biến thành một vệt mờ không đọc được chữ.
- **Phản ứng của User:** Gay gắt chất vấn: *"Còn hình m gửi có phải lúc nhập code bị lỗi đâu sao t biết đc m ns đúng hay k? Ủa t thiết kế gate rule gì đó ép m đọc hình trc khi gửi r mà"*. Mặc dù Agent đã đọc OCR và thấy lỗi, nhưng bằng chứng gửi cho User lại không thể tự minh chứng (Illegible Evidence).

## 2. Nguyên tắc "Bằng chứng phải tự chứng minh" (Self-Evident Proof)
1. **CẤM gửi duy nhất ảnh toàn màn hình dọc dài ngoằng cho các lỗi cục bộ:** Ảnh 1080x1920 hoặc web full-page dài hàng ngàn pixel chỉ có giá trị chứng minh ngữ cảnh chung, KHÔNG ĐỦ để chứng minh các chi tiết chữ nhỏ, popup, toast, status message hoặc validation lỗi.
2. **BẮT BUỘC gửi kèm ẢNH CROP CẬN CẢNH (Zoomed Focus Crop):**
   - Với mọi thao tác form, click nút, nhập code, xác thực lỗi hoặc verify thông báo: BẮT BUỘC dùng PIL/Image crop trích xuất đúng vùng chữ nhật trọng tâm (Target Bounds + 50-80px padding).
   - Ảnh crop phải đạt kích thước hiển thị rõ nét từng chữ ngay trong bubble chat của Telegram mà User không cần phải nhấp vào ảnh để zoom tay.
3. **Quy trình Crop chuẩn bằng Python:**
   ```python
   from PIL import Image
   im = Image.open(screenshot_path)
   # Crop đúng vùng mục tiêu: (left, top, right, bottom)
   crop_box = im.crop((50, target_y_start - 50, 1030, target_y_end + 100))
   crop_box.save(crop_path)
   ```
4. **Tránh bẫy bàn phím ảo che mất thông tin:**
   - Khi nhập text xong, bàn phím ảo (SamsungKeypad/AdbKeyboard) có thể che mất nút Submit hoặc dòng thông báo lỗi bên dưới.
   - Luôn gửi `input keyevent 4` (BACK) hoặc tap vùng trống ngoài form để ẩn bàn phím ảo trước khi chụp ảnh nghiệm thu Post-submit.
5. **Cặp đôi Bằng Chứng: OCR Quote + Crop Image:**
   - Text chat: Trích dẫn nguyên văn (verbatim) dòng chữ OCR đọc được.
   - Media: Gửi dòng `MEDIA:<crop_path>` ngay dưới mô tả để đối chiếu trực tiếp.
