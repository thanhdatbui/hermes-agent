# Bài Học Thực Chiến: Regex DIRTY_AVATAR False-Positive & Lệch SHA256 Trên Proposal Canvas

## 1. Bối Cảnh Sự Cố (Root Cause)
Trong phiên chuẩn hóa avatar kênh TikTok farm (@vyvy14190 trên Máy 274), Agent liên tục gặp tình trạng thẻ `MEDIA:` bị gate `guard_media_vision_gate.py` âm thầm cắt cụt (strip), khiến tin nhắn gửi về Telegram chỉ có text suông mà không có ảnh, dẫn đến việc User bức xúc vì cho rằng Agent không gửi bằng chứng.

## 2. Hai Lỗ Hổng Cơ Học Được Phát Hiện

### Kẽ hở 1: Regex DIRTY_AVATAR_EVIDENCE tự bắn vào chân
* **Cơ chế cũ:**
  ```python
  if is_visual_image and "avatar" in img_lower:
      if "play" in ocr or re.search(r"(?<!\w)(?:\d{1,3}(?:[.,]\d{3})+|\d{3,})(?!\w)", ocr):
          return _verdict("DIRTY_AVATAR_EVIDENCE", ...)
  ```
* **Hiện tượng:** Regex nhằm phát hiện số view video grid (`10.5K`, `1200`), nhưng file canvas lại tên là `avatar_proposals_m274_vyvy14190.jpg` (chứa `avatar`) và trên canvas in text `274` (số máy).
* **Hậu quả:** Regex bắt trúng số `274` ($\ge 3$ chữ số) ➔ Gate gán nhãn `DIRTY_AVATAR_EVIDENCE` và drop sạch thẻ `MEDIA:`.
* **Khắc phục:** Tách biệt ranh giới: Chỉ áp dụng dirty check cho ảnh avatar crop thuần túy (`is_pure_crop = "proposal" not in img_lower and "canvas" not in img_lower`). Proposal canvas được phép in số máy.

### Kẽ hở 2: Lệch SHA256 Sau Khi Re-render Canvas
* **Hiện tượng:** Khi code generator chỉnh sửa lại canvas (đổi text, chỉnh tọa độ crop), file ảnh trên đĩa có SHA256 mới.
* **Hậu quả:** Receipt cũ lưu SHA256 của file trước đó. Khi kiểm tra chữ ký HMAC và hash file thật:
  `r.get('sha256') == _sha256_file(canvas) -> False`
  Gate đánh rớt với lỗi `NO_RECEIPT` và tiếp tục strip `MEDIA:`.
* **Khắc phục:** Sau khi ghi đè canvas, bắt buộc phải re-register receipt mới khớp với SHA256 mới nhất trước khi gọi gate.

## 3. Lỗi Ảo Giác Tọa Độ Crop (Hallucinated Crop Coordinates)
* **Sai lầm:** Khi ảnh nguồn là toàn cảnh (ví dụ cún cuộn mình trên thảm, đầu nằm ở góc trên bên phải `y: 20-260, x: 230-470`), script crop lấy tâm `(H//2, W//2)` dẫn đến ô tròn chỉ chứa mảng lông lưng/thân, không hề có mặt/mắt/mũi.
* **Quy tắc bắt buộc:**
  1. Khi crop cận cảnh khuôn mặt (close-up), bắt buộc chia 4 góc phần tư hoặc detect bounding box để crop đúng vùng đầu.
  2. Dùng `browser_vision` mở trực tiếp file crop lẻ để xác nhận có đủ 2 mắt, mũi, tai trước khi đưa vào canvas.
