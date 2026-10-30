# Bẫy Thuật Ngữ "Vision Check Bằng Lời" Nhưng Không Gửi Thẻ MEDIA:

## 1. Hiện Tượng & Phản Hồi Thực Tế Của User
Trong phiên làm việc tương tác desktop UI (cài đặt Spend Alert DigitalOcean):
- Coordinator điều khiển Chrome qua `computer_use(action='capture', mode='som')` và đọc trường `vision_analysis` do tool trả về.
- Sau khi click lưu cài đặt thành công, Coordinator tự tin thông báo với User bằng câu văn:
  > *(Vision check trên giao diện DigitalOcean xác nhận thẻ alert đã lưu thành công: Monthly budget: $15 / month, Thresholds: 50%, 75%, 100%).*
- Tuy nhiên, trong tin nhắn đó Coordinator **hoàn toàn không đính kèm thẻ `MEDIA:<path_anh>`** để gửi ảnh thực tế cho User xem.
- User lập tức tức giận phản hồi gắt gao:
  > `[Replying to: "(Vision check trên giao diện DigitalOcean xác nhận thẻ alert đã lưu thành công: Monthly budget: $15 / month, Thresholds: 50%, 75%, 100%)."]`
  > `có gửi hình lồn đâu`

## 2. Nguyên Nhân Gốc (Root Cause)
1. **Ảo giác hoàn thành qua "Vision Check bằng lời"**:
   Coordinator nhầm lẫn giữa việc "mình (LLM) đã thấy ảnh thông qua tool `computer_use` / `browser_vision`" với việc "User trên Telegram đã thấy ảnh".
2. **Không phân biệt giữa Vision nội bộ và Bằng chứng người dùng**:
   Khi Coordinator ghi chú `(Vision check xác nhận...)`, User mặc định kỳ vọng sẽ có một bức ảnh chụp màn hình đính kèm ngay bên dưới. Việc nói "đã vision check" mà không gửi ảnh bị User coi là "nói mồm", "chạy mù lấp liếm" hoặc thất hứa vi phạm Gate 6.
3. **Kỷ luật Gate 6 trên Desktop / Web UI**:
   Gate 6 quy định: *MỌI THAO TÁC TRÊN GIAO DIỆN (BROWSER, GPM, UI, FARM, APP, WEB) BẮT BUỘC PHẢI CÓ ẢNH CHỨNG MINH THỰC TẾ. IM LẶNG HOẶC CHẠY MÙ = VI PHẠM TRỰC TIẾP.*
   Nếu đã thao tác UI và khẳng định đã xác minh, BẮT BUỘC phải xuất file ảnh chụp màn hình ra đĩa và đính kèm thẻ `MEDIA:<path_anh>` ngay trong câu trả lời.

## 3. Quy Chuẩn Xử Lý Chuẩn (SOP)
1. **Invariant: Có chữ "Vision check" là BẮT BUỘC phải có thẻ `MEDIA:<path>`**:
   - Tuyệt đối CẤM viết các câu khẳng định kiểu *"Vision check xác nhận..."*, *"Đã soi mắt thấy..."*, *"Hình ảnh cho thấy..."* mà không kẹp thẻ `MEDIA:<path>` trong cùng tin nhắn.
   - Nếu không gửi được ảnh (do lỗi kỹ thuật), phải báo trung thực trạng thái text, cấm dùng thuật ngữ "Vision check" tạo kỳ vọng ảo cho User.

2. **Cách xuất ảnh chụp màn hình máy tính để gửi MEDIA: khi dùng computer_use**:
   Khi thao tác ứng dụng desktop hoặc trình duyệt ngoài luồng ADB (như Chrome desktop), `computer_use` chụp ảnh vào cache nội bộ của driver. Để gửi cho User qua Telegram:
   - Dùng Python script 1 dòng lưu màn hình ra thư mục hợp lệ (ví dụ `D:/Taadaa/reports/<ten_anh>.png`):
     ```python
     from PIL import ImageGrab
     im = ImageGrab.grab() # hoặc crop vùng cửa sổ
     im.save('D:/Taadaa/reports/evidence.png')
     ```
   - Chạy `browser_vision` để hợp thức hóa receipt (Gate Media Guard):
     ```python
     browser_vision(question="Kiểm tra bằng chứng...")
     ```
   - Đính kèm thẻ `MEDIA:D:/Taadaa/reports/evidence.png` vào tin nhắn trả về.
