# Reference: Invariant Live Device Proof vs Cronjob Schedule Illusion (2026-09-17)

## Sự Cố Thực Tế (Phản Ứng Gắt Từ User)
- **Bối cảnh:** User hỏi: *"Máy 30 nay log in tiếp mấy acc kia chưa?"*.
- **Hành vi sai lầm của Agent:**
  1. Agent chỉ nhìn vào bảng `cronjob(action='list')`, thấy job `retry-security-limit-m30-24h` có `next_run_at: 10:45:00` (còn 10 phút nữa mới tới giờ).
  2. Agent vội vàng trả lời văn bản: *"Dạ chưa chạy anh ạ, còn 10 phút nữa cron mới kích hoạt"*, mà **KHÔNG HỀ CHẠM VÀO THIẾT BỊ ĐỂ INSPECT THỰC TẾ**.
  3. Khi user bức xúc: *"Gì thế bằng chứng của mày như lồn v"*, Agent mới giật mình thức tỉnh:
     - Chụp screencap màn hình Máy 30.
     - Mở Account Switcher (`Chuyển đổi tài khoản`).
     - Chạy WinRT OCR đọc text màn hình.
     - **Bằng chứng thực tế:** Chỉ có duy nhất 1 nick `ninhvan04061999`, không có nick nào khác!
     - Khi đó gửi ảnh `MEDIA:D:\Taadaa\m30_accounts_dropdown_live.png` kèm OCR mới là **BẰNG CHỨNG HỢP LỆ VÀ ĐƯỢC CHẤP NHẬN**.

## Căn Bệnh Gốc Rễ (Root Cause)
- **Schedule Illusion (Ảo tưởng lịch trình):** Nhầm lẫn giữa "Trạng thái lịch trình phần mềm (cron schedule)" và "Hiện trạng vật lý thực tế trên thiết bị (Physical Device State)".
- Khi User hỏi về trạng thái một thiết bị (*"đã làm X chưa?", "đã đăng nhập chưa?", "máy đang ở đâu?"*), User đang đòi hỏi **BẰNG CHỨNG HIỆN TRƯỜNG THỰC TẾ (Physical Live Proof)**, KHÔNG PHẢI một câu trả lời lý thuyết dựa trên bảng lịch cron.
- Trả lời chay mà không đính kèm ảnh/OCR thực tế tại thời điểm hỏi bị coi là vi phạm nghiêm trọng kỷ luật bằng chứng.

## Quy Tắc Cứng: Physical Live Inspection First
Khi nhận bất kỳ câu hỏi nào về tình trạng của một máy/tài khoản farm:
1. **CẤM trả lời chay từ cron/database:** Tuyệt đối không được chỉ kiểm tra file log, database hay cron schedule rồi kết luận máy đã làm hay chưa làm.
2. **BẮT BUỘC Inspect thiết bị ngay turn đầu:**
   - Đánh thức máy (`input keyevent 224`, `dismiss-keyguard`).
   - Mở màn hình chứa trạng thái cần kiểm chứng (ví dụ: Account Switcher để kiểm tra danh sách nick).
   - Screencap + chạy WinRT OCR bóc tách văn bản.
3. **Báo cáo bằng chứng trước, lịch trình sau:**
   - Dòng đầu tiên gửi ảnh thực tế (`MEDIA:<path>`).
   - Trích dẫn text OCR xác thực hiện trạng máy.
   - Sau đó mới giải thích bổ sung về tiến độ hoặc lịch hẹn cronjob.
