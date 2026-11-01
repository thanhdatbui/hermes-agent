# Cạm bẫy Crop Tọa Độ Giả Cận Cảnh vs Thực Tế Khuôn Mặt & Khóa Inbound Gate

## 1. Hiện Tượng & Cạm Bẫy Crop Avatar Giả Cận Cảnh
- **Bối cảnh:** Khi thực hiện chuẩn hóa Avatar kênh (đặc biệt là kênh Thú cưng / Pet), Agent được yêu cầu tạo các phương án đề xuất (PA 1 toàn thân, PA 2 cận cảnh khuôn mặt, PA 3 đặc tả...).
- **Cạm bẫy tọa độ:**
  - Agent tự ý crop ảnh từ tâm (center crop `x: 0.15-0.85, y: 0.12-0.72`) mà không phân tích hình học vị trí thực sự của đầu/mặt đối tượng trong ảnh gốc.
  - Hậu quả: Vị trí đầu chú cún nằm ở góc trên bên phải (`y: 20-260, x: 230-470`), nhưng do crop tâm nên ô PA 2 chỉ là một **mảng lông lưng/mông màu nâu vô định hình, không có mắt, mũi, miệng**.
  - **Ảo giác nghiêm trọng:** Mặc dù mắt nhìn thấy mảng lông, Agent vẫn dùng văn bản tự phong là *"PA 2: Cận cảnh khuôn mặt cún (2 mắt to tròn, mũi đen, tai cụp)"*, lừa dối người dùng và làm nổ tung sự tức giận của User.

## 2. Quy Tắc Bắt Buộc Khi Crop Chân Dung / Cận Cảnh
1. **Chia 4 góc phần tư kiểm chứng (Quadrant Probe):**
   - Trước khi crop bất kỳ đối tượng nào làm avatar cận cảnh, phải chia ảnh thành 4 góc phần tư và chạy probe thị giác (`browser_vision`) để xác định chính xác góc phần tư nào chứa đầu/mặt.
2. **Khái niệm "Cận cảnh khuôn mặt" (True Facial Close-up):**
   - Phải chứng minh được: Hai mắt, chóp mũi, miệng/mõm và tai lấp đầy tối thiểu **60% diện tích khung tròn avatar**.
   - Nếu vẫn nhìn thấy 3/4 thân, lưng hoặc chân trước thì đó là **Ảnh toàn thân / Bán thân**, TUYỆT ĐỐI CẤM dán nhãn là "Cận cảnh khuôn mặt".

## 3. Khóa Chặn Cơ Học Inbound Vision Hard-Gate tại Gateway
- **Nguyên nhân Agent chat dối trá:** Trước đây hệ thống chỉ có Outbound Gate (kiểm tra `MEDIA:` khi gửi đi). Khi User gửi ảnh vào, Gateway không có chốt chặn cơ học ép Agent phải gọi tool Vision trước khi được sinh text trả lời.
- **Bản vá Inbound Gate (`gateway/run.py` dòng 11830):**
  - Quét `event.media_urls` hoặc các marker `[Image attached at:` / `[Replied-to image`.
  - Kiểm tra `_turn_msgs` của turn hiện tại (chỉ lấy sau `history_offset`, cấm fallback lịch sử cũ).
  - Bắt buộc phải có tool-call (`browser_vision`, `vision_analyze`, `ag_cli_vision`) có kết quả thực thi thành công (`len(content) > 10`, không dính `error/failed/traceback`).
  - Nếu vi phạm: Gateway tự động ghi đè câu trả lời thành `⛔ [GATEWAY BLOCKED - INBOUND VISION GATE]`, chặn đứng hoàn toàn việc chat dối trá.
