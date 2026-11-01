# Cạm Bẫy Crop Tọa Độ Avatar & Lỗ Hổng Bỏ Sót Windows Inbound Path (2026-11-01)

## 1. Cạm Bẫy Crop Tọa Độ Giữa Ảnh (Center-Crop vs Subject Head Location)
- **Hiện tượng**: Khi lấy avatar từ ảnh nằm hoặc ảnh toàn thân thú cưng (như `avatar.jpg`), việc crop mù vào tọa độ trung tâm hình học (`x: W/2, y: H/2`) thường chỉ lấy trúng **lưng, sườn hoặc mảng lông không đầu**.
- **Hậu quả**: Khi model bị ảo giác ngữ nghĩa, nó vẫn mô tả với người dùng là "cận cảnh khuôn mặt, 2 mắt, mũi đen", nhưng thực tế hình gửi là mảng lông vô hình vô dạng, gây mất uy tín nghiêm trọng.
- **Quy trình chuẩn**:
  1. Phải chia ảnh gốc thành 4 góc phần tư (`dbg_quad_top_left`, `top_right`, v.v.) để xác định chính xác tọa độ đầu của chủ thể qua `browser_vision`.
  2. Với ảnh cún cuộn mình nằm thảm: đầu thường nằm ở góc trên bên phải (`y: 20-260, x: 230-470`).
  3. BẮT BUỘC soi mắt trực tiếp từng crop trước khi dán vào Canvas.

## 2. Inbound Vision Hard-Gate & Bẫy Windows Drive Path trong image_routing
- **Nguyên nhân cốt lõi**:
  - `guard_media_vision_gate.py` trước đây chỉ là Outbound Gate (chặn khi có thẻ `MEDIA:`).
  - Khi User gửi ảnh vào Telegram, Gateway chỉ inject text: `[Image attached at: C:\Users\Kibe\...]`.
  - Regex `_LOCAL_IMAGE_PATH_RE` trong `image_routing.py` chỉ match POSIX path (`/` hoặc `~/`), hoàn toàn không match ổ đĩa Windows `C:\` kèm dấu `\`.
  - Hậu quả: Hermes không attach native multimodal image vào model, khiến model nhận tin nhắn text thuần không có pixel, dẫn đến ảo giác và phán bừa.
- **Bản vá Inbound Gate tại `gateway/run.py`**:
  - Khi inbound message có ảnh (`event.media_urls` hoặc text chứa marker ảnh), Gateway bắt buộc kiểm tra transcript turn hiện tại.
  - Bắt buộc phải có tool call `browser_vision` hoặc `vision_analyze` thành công (`content > 10` ký tự và không dính error).
  - Nếu Agent chưa gọi tool vision mà dám sinh text trả lời -> Gateway ghi đè response thành `⛔ [GATEWAY BLOCKED - INBOUND VISION GATE]` (Fail-Closed 100%).
