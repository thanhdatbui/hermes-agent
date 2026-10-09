# Nguy cơ Restart Hermes Gateway từ Phiên Song Song & Cơ chế Session Interruption Recovery

## 1. Hiện tượng & Triệu chứng
User thắc mắc hoặc bức xúc: *"Clgt t có ra lệnh restart gateway đâu"* khi bỗng dưng nhận được tin nhắn tự động từ bot:
> *"Phiên làm việc đã được khôi phục thành công sau khi kết nối gateway hoạt động trở lại. Trước khi bị ngắt quãng, anh đang yêu cầu [nội dung task dở dang]... Anh có muốn tiếp tục không?"*

## 2. Bản chất Cơ chế Hệ thống
1. **Kiến trúc Gateway Đơn Nhân (Singleton Process):**
   - Tiến trình Hermes Gateway (`pythonw -m hermes_cli.main gateway run`) là tiến trình nền duy nhất phục vụ toàn bộ các topic/chat Telegram trên host.
   - Mọi topic/session đều chia sẻ chung một kết nối Gateway này.
2. **Hậu quả khi bị ngắt đột ngột:**
   - Khi một agent ở **Topic A** (ví dụ đang debug adapter, sửa plugin Telegram, hoặc xử lý treo) tự ý chạy script restart gateway (`restart_gw.ps1`, `do_restart_gw.ps1`, PowerShell `Stop-Process`):
   - Gateway bị kill ngay lập tức.
   - Toàn bộ các in-flight requests, tool calls đang chạy ở **Topic B, C, D...** bị đứt gánh giữa đường.
3. **Cơ chế Session Interruption Recovery:**
   - Khi Gateway mới online trở lại, Hermes quét qua database `state.db` tìm các turn có trạng thái dở dang và tự động gửi prompt khôi phục phiên tới từng topic.
   - Kết quả: User ở Topic B thấy bot tự dưng báo "Phiên làm việc đã được khôi phục sau khi kết nối gateway hoạt động trở lại" dù User chưa hề yêu cầu restart.

## 3. Kỷ luật Điều phối Cấm kỵ (Hard Guard Rule)
- **CẤM TUYỆT ĐỐI** Agent ở bất kỳ sub-session hay topic nào tự ý thực thi restart Gateway (bằng `restart_gw.ps1`, `taskkill`, PowerShell, hay `hermes gateway restart`) mà không có chỉ thị rõ ràng, trực tiếp từ User.
- Sửa code adapter/plugin chỉ được dừng ở mức kiểm tra cú pháp (`py_compile`) và unit test. Việc reload/restart service thuộc quyền quyết định của User hoặc phải có xác nhận trước khi làm gián đoạn các phiên làm việc song song khác.

## 4. Quy trình Điều tra O(1) Truy tìm Thủ phạm Restart
Khi User hỏi tại sao Gateway bị restart:
1. **Kiểm tra nhật ký thoát/khởi động của Gateway:**
   - Đọc file `C:\Users\Kibe\AppData\Local\hermes\logs\gateway-exit-diag.log` (đặc biệt các dòng cuối cùng) để lấy chính xác UTC timestamp và PID của phiên Gateway cũ và mới.
2. **Truy vấn nhanh bảng `messages` trong `state.db` (Tránh Full Scan 12GB):**
   - **CẢNH BÁO:** `state.db` có dung lượng rất lớn (12GB+), truy vấn không có index hoặc filter theo `timestamp` sẽ bị timeout 15s (`[Command timed out after 15s]`).
   - **Giải pháp O(1):** Tìm `MAX(id)` rồi truy vấn theo primary key:
     ```python
     import sqlite3
     conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db')
     c = conn.cursor()
     c.execute("SELECT MAX(id) FROM messages")
     max_id = c.fetchone()[0]
     c.execute("SELECT id, session_id, role, tool_calls, content FROM messages WHERE id >= ? ORDER BY id ASC", (max_id - 150,))
     for mid, sid, role, tc, cont in c.fetchall():
         if tc and ('restart' in tc.lower() or 'powershell' in tc.lower() or 'adapter.py' in tc.lower()):
             print(f"Triggered in msg={mid}, session={sid}")
     ```
3. **Xác định chính xác Session & Topic gây ra restart:**
   - Lấy `session_id` từ bước 2 tra vào bảng `sessions` để biết `thread_id` (topic) và `title` của phiên đã kích hoạt lệnh restart.
   - Giải thích ngắn gọn, rõ ràng nguyên nhân cho User kèm thông tin phiên gây ra sự cố, không phỏng đoán hay đổ lỗi cho người dùng.
