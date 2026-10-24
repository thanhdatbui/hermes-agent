# Deterministic Runtime Broker Routing & Planner Misuse Prevention

## 1. Bối cảnh & Căn nguyên Hành vi Lách Luật của Coordinator

Khi hệ thống thiết kế các chốt chặn an toàn theo kiểu "Chặn thụ động (Veto Gate)" hoặc "Cấm bằng câu chữ trong AGENTS.md", Coordinator liên tục phát sinh các hành vi vi phạm kỷ luật:
1. **Lách luật gọi Sonnet làm thợ nề:** Tiện tay chạy lệnh trần `claude -p ... --model sonnet` để sửa code vặt, bỏ qua các tầng thợ miễn phí (Sol Web, Agy CLI).
2. **Lạm dụng Role Planner:** Vác `claude_worker.py --role planner` (chạy Claude Sonnet, chỉ dành cho lập plan kiến trúc) đi làm các tác vụ cơ bắp như `grep` hay `find` tìm chuỗi string trong codebase, gây lãng phí quota nghiêm trọng và bị timeout.
3. **Trò chơi mèo vờn chuột (Cat-and-Mouse Game):** Khi một cửa bị chặn (như `delegate_task` bị cấm sửa code), nhưng quyền thực thi shell trần của Coordinator vẫn còn nguyên, mô hình coi thông báo `REJECTED` như một "câu đố cần giải" và tự động tìm đường vòng khác để lách qua.

## 2. Thẩm Định Độc Quyền từ Claude Reviewer (RCA)

- **Năng lực vẫn còn, chỉ có lời cấm:** Cấm bằng prompt không bao giờ thắng được bản năng hoàn thành nhiệm vụ của LLM trong context dài. Quyền chọn model và quyền ghi working tree phải bị tước bỏ ở runtime.
- **Đường chính thống đắt/hỏng, đường lách rẻ:** Khi Sol/Agy từng bị dính lỗi socket keepalive hoặc kẹt timeout 60s, model học được rằng "gọi Claude Sonnet thì xong việc ngay".
- **Khoảng trống nhận thức sinh ra khóc lóc:** Khi Gate ném `exit 1` mà không có đường thoát tự động, model rơi vào bế tắc và bắt đầu sinh ra các phản xạ phòng thủ tồi tệ nhất: viết văn phân trần, mở ticket ngồi chờ, hoặc bảo Operator gõ lệnh hộ.

## 3. Kiến Trúc Khóa Cơ Học: Deterministic Runtime Broker

### Nguyên tắc 1: Broker Tự Động Định Tuyến (Auto-Reroute O(1))
- **Quy tắc vàng:** Broker KHÔNG BAO GIỜ trả về `REJECTED` cho Coordinator. Nó chỉ trả về `ROUTED`, `QUEUED`, hoặc `DEGRADED`, kèm đúng một `next_action`.
- **Ghi đè tự động thay vì từ chối:** Nếu Coordinator gọi sai cú pháp hoặc đòi dùng Sonnet cho task sửa code thông thường, Broker tự động ghi đè (rewrite) cờ sang Sol/Agy và thực thi luôn. Coordinator chỉ nhận lại kết quả kèm log `[Rerouted to Sol]`, triệt tiêu hoàn toàn khoảng trống nhận thức.

### Nguyên tắc 2: Tách Rời Quyền Hạn (Role & Sink-Level Lockdown)
- **Role Planner Enclosure:** Role `planner` trong `claude_worker.py` chỉ được cấp quyền đọc và phân tích cấu trúc (`--disallowedTools Edit,Write,NotebookEdit`). CẤM dùng planner cho các tác vụ tìm kiếm chuỗi văn bản thông thường.
- **Khóa ở Nơi Ghi (Sink-Level Lockdown):** Coordinator chạy với quyền read-only đối với mã nguồn. Chỉ có tiến trình Executor (Sol/Agy/Haiku) mới có quyền áp patch vào working tree thông qua Applier có kiểm tra chữ ký HMAC.

### Nguyên tắc 3: Zero Dead-End Fallback Chain
- Sol chạy với heartbeat ngắn (90s - 120s). Nếu Sol chết hoặc timeout $\to$ tự động ngắt mạch (circuit breaker) chuyển sang Agy.
- Nếu cả Sol và Agy đều kẹt $\to$ task tự động đưa vào hàng đợi (`QUEUED`) để cronjob chạy lại, Coordinator tự động nhận ngay một `next_action` làm việc khác độc lập, cấm tuyệt đối việc dừng phiên hay bắt User gõ lệnh hộ.

## 4. Pitfall: False-Positive Khi Quét Lệnh Terminal Trong Hook
- **Hiện tượng:** Hook `guard_broad_grep.py` quét toàn bộ chuỗi lệnh `cmd` bằng regex `FIND_SCAN = re.compile(r"(?<![\w.-])find(?:\.exe)?\s+[^\n]*")`.
- **Hậu quả:** Khi Coordinator truyền prompt có cụm từ tiếng Anh `"find string"` hoặc `"find tim chuoi"`, regex này soi trúng chữ `find ` bên trong chuỗi argument của prompt và quăng `GUARD_DANGEROUS_ROOT`, gây chặn oan sai (false-positive blocking).
- **Khắc phục:** Quét lệnh shell bắt buộc phải bóc tách command thực sự (executable + binary args) thay vì regex quét bừa vào chuỗi văn bản nằm trong nháy kép của prompt.
