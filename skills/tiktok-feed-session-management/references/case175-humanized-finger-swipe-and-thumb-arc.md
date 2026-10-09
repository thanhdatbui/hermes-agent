# Case 175: Humanized Finger Swipe (Vuốt Ngón Tay Sinh Học) & Cắt Bỏ Over-Engineering Đo Nhiệt Độ

## 1. Bối cảnh & Hiện Trạng
- **Vấn đề máy móc:** Trước đây `feed_swipe_smoke.py` dùng `DEFAULT_SWIPE_DURATION_MS = 650` (550ms – 750ms). Tốc độ vuốt này quá chậm, giống hành vi kéo rê chuột của bot hơn là cú quẹt ngón tay dứt khoát của người dùng thật (thực tế người dùng lướt TikTok chỉ mất 220ms – 400ms).
- **Độ nghiêng cơ học:** Vuốt ADB `input swipe` đi theo đường thẳng tắp, thiếu độ trượt tự nhiên của ngón cái xoay quanh khớp cổ tay (Thumb Arc).

## 2. Giải Pháp Kỹ Thuật (Case 175 Fix)

### A. Thời lượng vuốt dứt khoát (Biến thiên sinh học)
- `DEFAULT_SWIPE_DURATION_MIN_MS = 240` (thay vì 550)
- `DEFAULT_SWIPE_DURATION_MAX_MS = 400` (thay vì 750)
- `DEFAULT_SWIPE_DURATION_MS = 330` (thay vì 650)
- `DEFAULT_FEED_SWIPE_UP_COMMAND = ["input", "swipe", "450", "1380", "450", "480", "330"]`

### B. Độ nghiêng ngón cái tự nhiên (Thumb Arc Drift)
- Điểm chạm `start_x`: Phân bổ tự nhiên vùng tay phải `[470, 525]` (vùng giữa màn hình 1080px).
- Độ nghiêng xoay cổ tay `drift`: Biến thiên ngẫu nhiên từ `-35px` (nghiêng nhẹ sang trái theo chiều ngón cái) đến `+15px`.
- Hành lang an toàn `end_x`: Clamped bên trong `[440, 540]` (cách mép trái >440px và cách cột tương tác phải >360px, tuyệt đối không chạm nhầm nút Like/Share hay thanh tìm kiếm).
- Tọa độ Y: `start_y: 1330 – 1410`, `end_y: 430 – 510` (quãng đường vuốt 820px – 980px, đủ để TikTok kích hoạt fling chuyển video trơn tru).

### C. Bẫy ẩn triệt tiêu độ nghiêng trong `_perform_feed_swipe` (Root Cause Trap)
- Trong `_perform_feed_swipe`:
  ```python
  # CŨ: nếu |dx| > 30px thì ép end_x = start_x (biến thành đường thẳng đứng)
  if abs(raw_end_x - start_x) > 30:
      end[0] = start_x
  ```
  Nếu drift đặt `-35px` mà không nâng ngưỡng này, toàn bộ các cú vuốt nghiêng > 30px sẽ bị hàm kiểm tra an toàn ép ngược về đường thẳng đứng!
- **Fix:** Nâng ngưỡng skew lên `|dx| > 45px` và nới corridor an toàn sang `[440, 540]`:
  ```python
  if abs(raw_end_x - start_x) > 45:
      end[0] = start_x
  else:
      end[0] = max(440, min(540, raw_end_x))
  ```

## 3. Kỷ Luật Vận Hành: Chống Over-Engineering "Đo Nhiệt Độ Máy" (User Correction 2026-09-16)
- **Cảnh báo bẫy lý thuyết:** Khi xin ý kiến các mô hình tư vấn kiến trúc (như Sol), mô hình thường đề xuất thêm telemetry phần cứng (nhiệt độ CPU/pin, RAM, storage) và tự động bóp quota cày khi máy nóng.
- **Kỷ luật thực chiến farm:** Trên dàn 160 máy Galaxy S7 đặt trong box có quạt tản nhiệt, máy nóng khi cày cuốc liên tục là hiện tượng bình thường. Tự ý hạ quota hay dừng cày vì máy nóng làm thụt lùi hiệu suất farm.
- **Quy chuẩn Telemetry Sức Khỏe:** CHỈ theo dõi các chỉ số cấp tài khoản (Account-level):
  1. Tỷ lệ nhả follow (`verify_follow.py`).
  2. Hiện tượng dính "0-View Jail" sau 24h trên lưới video Profile.
  3. Khi dính 0-View hoặc phạt liên tục: Kích hoạt Deep Organic Rest 3 ngày (pure feed, 0 follow, 0 upload). Không phụ thuộc vào nhiệt độ phần cứng.
