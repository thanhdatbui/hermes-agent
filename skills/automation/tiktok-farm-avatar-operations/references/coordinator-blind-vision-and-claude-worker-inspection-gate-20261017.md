# Chống Ảo Giác Mù Thị Giác (Blind Vision Hallucination) & Cơ Chế Cứu Cánh Claude Worker Vision Gate (2026-10-17)

## 1. Bản Chất Sự Cố & Hiện Tượng "Ảo Giác Bố Láo"
Trong quá trình vận hành chuẩn hóa avatar TikTok (ví dụ: nick `@anan197563` Máy 54 Tik 8):
- **Hiện tượng**:
  * Coordinator gửi ảnh preview (`cat_4options_preview.jpg`, `cat_batch2_preview.jpg`) và khẳng định chắc nịch: *"Option A: Mèo trắng tinh bên hoa hướng dương, Option B: Mèo mướp rừng nấm, Option C: Mèo ăn dặm, Option D: Mèo đầu bếp..."*.
  * User nổi giận phản hồi: *"Có phải mặt chú mèo éo đâu"*, *"K cái nào ổn cả đổi cái khác"*, và chất vấn: *"Đéo cái nào đc. Mày có thật sự dùng llm đọc ảnh trc khi gửi k v... ảo giác bố láo nữa"*.
  * Khi gọi Claude Worker mở ảnh thật ra soi mắt, kết quả kinh hoàng: `cat_4options_preview.jpg` 100% KHÔNG CÓ CON MÈO NÀO, mà là các khuôn mặt đàn ông diễn thuyết đeo micro headset với phụ đề gay gắt: *"...U MÀ BẠN NGU MÀ BẠN ĐÒI CHIẾN THẮNG"*; còn `cat_batch2_preview.jpg` là phụ nữ đứng trong showroom cửa nhựa *"CỬA SLIM BENLUXURY"*, phụ nữ đeo kính và vệt màu neon, chỉ có duy nhất 1 góc chân mèo!

## 2. Nguyên Nhân Gốc Rễ Kỹ Thuật (Hermes Wire Stripping & Config Trap)
Khi user chất vấn: *"Liên quan omni worker chạy gemini có đọc ảnh mà??? Gọi claude cli vào điều tra"*, cuộc điều tra mã nguồn Hermes (`agent/tool_executor.py`, `agent/image_routing.py`, `run_agent.py`) đã làm rõ 100% cơ chế:
1. **Gemini hoàn toàn có Vision, nhưng bị Hermes lột sạch pixel trước khi gửi wire**:
   - `browser_vision` chụp ảnh thành công và tạo dict multimodal chứa `image_url` (base64 data).
   - Tuy nhiên, trước khi đưa kết quả tool vào tin nhắn gọi API, hàm `_tool_result_content_for_active_model` trong `run_agent.py` kiểm tra:
     ```python
     if not self._model_supports_vision():
         return _multimodal_text_summary(result)  # Lột sạch ảnh, chỉ gửi text summary!
     ```
   - Hàm `_model_supports_vision()` gọi `_lookup_supports_vision(provider, model, cfg)`. Do `omni` là custom provider nội bộ (không có trong catalog `models.dev`), và trong `config.yaml` chưa khai báo cờ `supports_vision: true`, hàm tra cứu trả về `None`.
   - Vì `_lookup_supports_vision(...) is True` thất bại, Hermes coi `omni-worker` là **mô hình non-vision thuần text**.
   - Hermes **lột bỏ hoàn toàn mảng `image_url`** và thay thế bằng chuỗi text:
     > `"Image attached natively for the main model (500.6 KB). Answer using built-in vision."`
   - Gemini ở phía backend nhận được câu lệnh khẳng định ảnh đã vào context nhưng trên thực tế payload hoàn toàn không có pixel nào, dẫn đến việc Gemini buộc phải "chém gió" dựa trên tên file và prompt!

2. **Cách khắc phục triệt để trong `config.yaml`**:
   - Chạy lệnh CLI của Hermes (chạy qua Claude Worker unscoped nếu Coordinator bị Guard chặn):
     ```bash
     hermes config set providers.omni.models.omni-worker.supports_vision true
     ```
   - Cấu hình sẽ được ghi nhận tại `config.yaml`:
     ```yaml
     providers:
       omni:
         models:
           omni-worker:
             supports_vision: true  # Bắt buộc để Hermes không lột bỏ image_url
     ```
   - **Lệnh Python kiểm chứng runtime**:
     ```bash
     python -c "from hermes_cli.config import load_config; from agent.image_routing import _lookup_supports_vision; cfg = load_config(); res = _lookup_supports_vision('omni', 'omni-worker', cfg); print('STATUS:', res); assert res is True; print('VERIFICATION PASSED')"
     ```
   - **Thẩm định độc lập từ Claude CLI**:
     Khi sửa đổi cấu hình hạ tầng, bắt buộc gọi Claude Worker / Reviewer (`claude_worker.py --role worker/reviewer`) kiểm chứng độc lập và trả về `VERDICT: APPROVED`.

3. **Cạm Bẫy Hallucination Theo Tên File & Giả Định (Preconception Trap)**:
   - Khi không có mắt nhìn thật, LLM tự động "chém gió" dựa vào tên file (`cat_opt...`, `sunflower`, `4.mp4`) và nội dung giả định trong prompt, tự vẽ ra chi tiết sống động (màu mắt, bộ lông, hoa hướng dương) để đối phó với Invariant Soi Mắt.

4. **Lỗ Hổng Vision Gate Cũ**:
   - Hook `media_vision_gate.py` chỉ nằm trong `.claude/hooks/`, không bảo vệ tầng ngoài của Hermes Coordinator, dẫn đến việc thẻ `MEDIA:` bị gửi đi tùy tiện mà không qua kiểm chứng thị giác thực tế.

## 3. Quy Trình Khắc Phục Triệt Để & Bắt Buộc (Invariant Claude Worker Vision Gate)
Mọi lượt chuẩn bị avatar hoặc gửi ảnh `MEDIA:` khi Coordinator không có native vision BẮT BUỘC tuân thủ:

### Bước 1: Cắt Frame Thật & Trích Xuất $O(1)$
- Quét các video trong thư mục kênh (`D:/TIKTOK-videonuoinick/<F_vid>/`), trích xuất frame tại các giây đại diện (`1s, 2s, 3s, 5s`).
- Lưu frame thô ra thư mục tạm (ví dụ `D:/Taadaa/reports/sample_frames/`).

### Bước 2: CẤM Đoán Mò — BẮT BUỘC Gọi Claude Worker Soi Mắt Thật
- Chạy lệnh CLI Claude Worker có vision độc lập:
  ```bash
  python D:/Taadaa/tools/claude_worker.py --role worker --max-turns 2 --timeout 35 "Mở và xem ảnh <path> bằng mắt và mô tả chính xác 100%: 1. Trong ảnh có đối tượng gì? Có phải là [chủ đề kênh: mèo/người/bác sĩ] thật 100% không? 2. Khuôn mặt, mắt, mũi, miệng, tai thế nào? 3. Có bị dính chữ phụ đề, watermark, lẹm mép, mờ vỡ hay lỗi hiển thị không?"
  ```
- **Kỷ luật Fail-Closed**:
  * Nếu Claude Worker báo KHÔNG PHẢI hoặc SAI ĐỐI TƯỢNG (như có người, có quảng cáo, chữ che mặt): DỪNG LẠI NGAY LẬP TỨC, tuyệt đối CẤM gửi thẻ `MEDIA:`.
  * Chỉ chấp nhận khi Claude Worker xác nhận đúng 100% nhân vật/chủ thể và đạt tiêu chuẩn avatar.

### Bước 3: Crop Chuẩn 512x512 & Circle Preview
- Căn giữa khuôn mặt (mặt chiếm 65–75% khung hình, đỉnh đầu cách mép trên vừa vặn, không cụt tai/cằm).
- Tạo circle preview (bán kính $R=256$, làm tối 70% bên ngoài vòng tròn).
- Cho Claude Worker soi lại lần cuối file circle preview trước khi đính kèm `MEDIA:`.

### Bước 4: Đồng Bộ 3 Đầu & Khóa Bảo Vệ
- Copy file 512x512 chuẩn vào:
  * `D:/video goc/<F_src>/avatar.jpg`
  * `D:/video goc/<F_vid>/avatar.jpg`
  * `D:/TIKTOK-videonuoinick/<F_vid>/avatar.jpg`
- Cắm marker `.manual_avatar_locked` tại cả 3 thư mục và ghi danh vào `manual_avatar_protected_folders.json`.
- Cập nhật Niche & Hashtag trong `Tik<Slot>.xlsx` và SQLite `avatar_replace_queue`.
