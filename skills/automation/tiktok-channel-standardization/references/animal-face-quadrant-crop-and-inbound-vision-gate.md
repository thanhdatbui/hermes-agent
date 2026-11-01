# Kỷ Luật Trích Xuất Avatar Khuôn Mặt Động Vật & Inbound Hard-Gate (2026-11-01)

## 1. Cạm Bẫy Crop Tọa Độ Giữa Tâm (Geometric Center vs Anatomy Head)
- **Vấn đề**: Khi tạo crop avatar từ ảnh toàn thân thú cưng (chó/mèo nằm trên sàn/thảm), việc resize hoặc crop theo tâm hình học `(W/2, H/2)` sẽ cắt trúng **lưng hoặc sườn**.
- **Hậu quả**: Ảnh hiển thị mảng lông vô hình dạng, nhưng Agent do ảo giác prompt vẫn khẳng định là "cận cảnh khuôn mặt, 2 mắt, mũi đen".
- **Kỷ luật**:
  1. Phải chia 4 góc phần tư để định vị chính xác vị trí đầu (`quadrant inspection`).
  2. Với ảnh cún nằm thảm của kho 589: đầu nằm ở góc phần tư trên bên phải (`y: 20-260, x: 230-470`).
  3. Bắt buộc soi mắt crop con trước khi ghép vào canvas 4 ô tròn.

## 2. Inbound Vision Hard-Gate tại Gateway
- **Cơ chế**: Tại `gateway/run.py` dòng 11830, khi inbound message có chứa ảnh (`event.media_urls` hoặc marker `[Image attached at:` / `[Replied-to image`), Gateway kích hoạt Inbound Vision Gate:
  - Bắt buộc transcript lượt hiện tại phải có tool call `browser_vision` hoặc `vision_analyze` thành công.
  - Nếu Agent chưa gọi tool vision mà dám sinh text trả lời -> Gateway ghi đè câu trả lời thành `⛔ [GATEWAY BLOCKED - INBOUND VISION GATE]` (Fail-Closed).
