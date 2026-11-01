# Telegram Image Delivery Limits & Viewport Crop SOP

## 1. Triệu Chứng & Lỗi
- **Triệu chứng:**
  - Tin nhắn Telegram hiển thị lỗi: `⚠️ Couldn't deliver the file attachment (<file_name>.png)`.
  - Trên tin nhắn chat của người dùng xuất hiện chuỗi văn bản thô `MEDIA:C:\Users\...` mà không hiển thị ảnh xem trước (photo preview).
- **Nguyên nhân gốc rễ:**
  1. **Bẫy chụp toàn trang 80.000 pixel (The 80k-Pixel Full-Page Trap):**
     - Các trang web có bảng danh sách dữ liệu lớn (như TikTok Farm Dashboard với 1.270 tài khoản) có chiều cao tài liệu thực tế lên tới **80.000+ pixels**.
     - Khi gọi `browser_vision`, trình duyệt chụp toàn bộ tài liệu (Full Document), sinh ra file PNG kích thước khổng lồ: ví dụ `(1264, 80934)` pixels với hơn **102 triệu điểm ảnh (102 Megapixels)** và dung lượng thô **12.4 MB**.
  2. **Vi phạm giới hạn kỹ thuật Telegram Bot API & JPEG Standard:**
     - **Telegram `sendPhoto` Hard Cap:** Dung lượng tối đa là **10 MB**, tổng kích thước `width + height` không được vượt quá **10.000 pixels**.
     - **Tiêu chuẩn JPEG quốc tế:** Chiều cao tối đa mà định dạng JPEG hỗ trợ là **65.535 pixels** ($2^{16}-1$). File cao 80.934 pixels sẽ văng lỗi `DecompressionBombWarning` và `OSError: broken data stream` khi encode sang JPEG.
     - Khi gửi qua Telegram, Bot API từ chối nhận ảnh vì vượt quá 10 MB và quá 10.000 px, dẫn đến Gateway trả về lỗi `⚠️ Couldn't deliver the file attachment` và để lại đường dẫn text thô.

## 2. Quy Trình Cắt Viewport & Nén JPEG Bắt Buộc (SOP)
Trước khi đính kèm bất kỳ ảnh chụp trang web dài / dashboard nào vào thẻ `MEDIA:<path>` trên Telegram:
1. **Luôn cắt theo khung nhìn thực tế (Viewport Cropping):**
   - Chỉ giữ lại phần giao diện trên cùng chứa Header, các thẻ KPI và Top 20 dòng xếp hạng:
   ```python
   crop_height = min(im.height, 1800) # Cắt tối đa 1.800px chiều cao
   viewport = im.crop((0, 0, im.width, crop_height))
   ```
2. **Nén sang JPEG chất lượng cao (85–90%):**
   - Lưu sang định dạng JPEG nhẹ (`< 500 KB - 1 MB`):
   ```python
   viewport.save(out_jpg, "JPEG", quality=90, optimize=True)
   ```
   - Dung lượng từ 12.4 MB sẽ giảm xuống chỉ còn ~250–300 KB, tải cực nhanh trên 4G điện thoại.
3. **Soi mắt nghiệm thu trước khi gửi:**
   - Dùng `browser_vision` kiểm tra lại file JPEG cắt cúp, đảm bảo hình ảnh sắc nét, đúng tỷ lệ, đầy đủ KPI trước khi xuất thẻ `MEDIA:<path>`.
