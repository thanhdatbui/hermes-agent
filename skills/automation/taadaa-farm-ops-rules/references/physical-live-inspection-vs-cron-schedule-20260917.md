# Physical Live Inspection First vs Cron Schedule Illusion (User Correction 2026-09-17)

## Bối cảnh sự cố
User hỏi: *"Máy 30 nay log in tiếp mấy acc kia chưa?"*.
Agent chỉ nhìn vào danh sách cronjob thấy `next_run_at: 10:45:00` (còn 10 phút nữa) và trả lời bằng văn bản: *"Chưa chạy anh ạ, còn 10 phút nữa mới đến giờ"*.
User bức xúc phản ứng gay gắt: *"Gì thế bằng chứng của mày như lồn v"*.

## Kỷ luật bắt buộc (Mandatory Rules)
1. **CẤM trả lời chay theo lịch cron / log:** Tuyệt đối không được chỉ kiểm tra trạng thái phần mềm (cron schedule, database, file log) rồi đưa ra kết luận về tình trạng máy/tài khoản.
2. **Turn 1 BẮT BUỘC chạm thiết bị:** Ngay khi nhận câu hỏi về tình trạng máy/acc:
   - Đánh thức máy qua ADB (`input keyevent 224`, `wm dismiss-keyguard`).
   - Mở màn hình đích có giá trị chứng minh (ví dụ: mở Account Switcher để kiểm tra danh sách tài khoản thực tế).
   - Screencap + chạy WinRT OCR bóc tách toàn bộ text trên màn hình.
3. **Evidence First:** Bắt buộc gửi ảnh hiện trường `MEDIA:<path>` ở dòng đầu tiên kèm kết quả OCR chứng minh trước, sau đó mới trình bày về tiến độ hoặc thời gian cronjob tiếp theo.
