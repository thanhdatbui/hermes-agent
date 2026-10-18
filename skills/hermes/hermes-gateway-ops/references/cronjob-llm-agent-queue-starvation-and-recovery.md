# Chẩn đoán & Xử lý Nghẽn Hàng Đợi Telegram Gateway do Cronjob LLM-Agent

## 1. Hiện Tượng Thực Tế
- Toàn bộ các bot/session Telegram của Operator bị "im lặng" (silent freeze) suốt 1-2 tiếng (ví dụ từ 11:00 đến 12:29).
- Operator gửi tin nhắn trong bất kỳ topic/DM nào đều không nhận được phản hồi.
- Đến khi hết nghẽn (ví dụ 12:25 - 12:29), Gateway đột ngột xả hàng loạt tin nhắn phản hồi dồn dập vào nhiều session cùng một lúc.
- Lầm tưởng phổ biến: Operator nghi ngờ Gateway bị restart làm mất phiên, hoặc nghi ngờ tiến trình nền bị kill.

## 2. Nguyên Nhân Gốc Rễ (Queue Saturation by LLM-Agent Cronjobs)
1. **Cronjob mặc định `no_agent: False` trong Hermes:**
   - Khi tạo cronjob bằng tool `cronjob(action='create')`, nếu quên truyền `no_agent: True`, scheduler coi đây là một task AI Agent.
   - Mỗi tick theo lịch (ví dụ `*/15 * * * *`), scheduler dựng một full LLM session mới.
2. **Vòng lặp Agentic Reasoning nuốt trọn kết nối LLM:**
   - Nếu script in stdout dài hoặc gặp lỗi, con AI Agent thức dậy tự động đọc log, suy luận, gọi tool, thử lại... liên tục kéo dài 50-80+ turns.
   - Các luồng kết nối tới API LLM (OmniRoute, Gemini, Anthropic) bị phiên cronjob này chiếm trọn.
3. **Cơ chế Message Queue của Gateway:**
   - Tin nhắn mới từ Telegram gửi tới Gateway vẫn được webhook/long-polling tiếp nhận nhưng bị đưa vào hàng đợi (Queue) chờ LLM runner rảnh rỗi.
   - Khi cronjob chạy xong 86 turns, hàng đợi mới được xả -> các tin nhắn bị ngâm suốt 1 tiếng rưỡi đồng loạt được xử lý cùng lúc.

## 3. Cách Chẩn Đoán Nhanh O(1)
1. **Kiểm tra danh sách cronjob:**
   Gọi `cronjob(action='list')` và kiểm tra các job có `no_agent: false` hoặc thiếu `no_agent`.
2. **Kiểm tra các session vừa hoạt động gần nhất:**
   Gọi `session_search(limit=10)` (browse shape). Tìm các session có prefix `cron_<job_id>_<timestamp>` và xem `message_count`. Nếu thấy `message_count: 50` đến `86`, đó chính là thủ phạm chiếm dụng LLM.
3. **Kiểm tra uptime của Gateway process:**
   Kiểm tra `%LOCALAPPDATA%\hermes\gateway-starts.log` và process `python.exe -m hermes_cli.main gateway run`. Nếu PID và create_time không đổi thì Gateway không hề restart, chỉ bị nghẽn queue.

## 4. Cách Khắc Phục Triệt Để
1. **Dừng khẩn cấp các job vi phạm:**
   Gọi `cronjob(action='pause', job_id='<id>')`.
2. **Triển khai Auto-Quarantine Scanner (`reconcile_cronjobs.py`):**
   Chạy `python D:/Taadaa/tools/reconcile_cronjobs.py --apply` để tự động đổi các job vi phạm sang `enabled: false`, `state: 'paused'`.
3. **Cưỡng chế PreToolUse Hook (`guard_cronjob_safety.py`):**
   Hook chặn đứng mọi hành vi tạo/sửa cronjob nếu thiếu `no_agent: True` (kiểu bool `is True`) hoặc thiếu script hợp lệ.
