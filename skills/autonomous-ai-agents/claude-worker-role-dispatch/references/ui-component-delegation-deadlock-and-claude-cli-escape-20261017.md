# UI Component Delegation Deadlock & Claude CLI Escape Valve (17/10/2026)

## 1. Incident Summary & User Pain Point
- **Context:** User requested improving the Follow Medical Record view on Dashboard (`http://localhost:1905`): "Cái giao diện sổ tay bệnh án follow trên db t thấy khó đọc quá. Sao k xếp theo danh sách nick khoẻ yếu, và làm riêng 1 tab hoặc sao đó. Chứ làm nhỏ khó đọc vc".
- **Execution Failure:** Task dragged on for nearly 2 hours without a single line of UI code changed. User reacted with extreme frustration: *"vkl t đéo hiểu làm 2 tiếng k xong, lí do? lí do sao mày điều phối ngu, rule điều phối k ổn à, gọi claude cli hỏi cho tao, hay do năng lực model chỉ đến v"*.
- **Resolution:** Claude Code CLI was consulted directly. It diagnosed the architectural deadlock, directly applied the Master-Detail 2-column layout to `D:/Taadaa/tools/dashboard/follow_detail_component.py`, restarted the server, and verified visual correctness in under 60 seconds.

---

## 2. Root Cause Analysis by Claude Code CLI

### A. Chi phí điều phối vượt xa chi phí công việc (Deadlock do thiết kế):
1. **Rule Coordinator bị trói cứng:** Coordinator bị cấm sửa > 15 dòng và chạm trần T1 budget (200 dòng), buộc phải dispatch Worker.
2. **Worker bị siết budget 15 calls:** Tác vụ sửa UI đòi hỏi đọc hiểu cấu trúc HTML, CSS và JavaScript. Worker subagent (`ag-gemini-pool-3`) ngốn 14/15 calls chỉ để đọc file và đo layout, chạm trần `WORKER GATE - BUDGET EXHAUSTED` và kích hoạt `ABORT_SCOPE` mà không viết được dòng code nào.
3. **Mô hình Worker Pool phụ không ổn định:** Khi Coordinator chuẩn hóa sẵn code vào context và dispatch lần 2, pool subagent bị timeout 600s (10 phút) không trả về kết quả.
4. **Hệ thống rơi vào bế tắc:** Rule cấm Coordinator làm trực tiếp, còn Worker thì không đủ khả năng/budget để làm thay.

### B. Over-engineering quy tắc điều phối:
- Áp đặt cơ chế O(1) và Circuit Breaker (vốn thiết kế cho farm lặp đi lặp lại) lên tác vụ UI/frontend.
- Thiếu "ngưỡng việc nhỏ" (Small task bypass): Việc chạm ≤ 1-2 file, rủi ro thấp, người dùng đang đợi nhưng vẫn bị ép qua chuỗi ủy quyền 3 tầng cồng kềnh.
- Bẫy ngụy tạo cờ `WORKER_CLI_EXHAUSTED: true` để ép subagent chạy khi subagent vốn không phù hợp cho tác vụ code/test phức tạp.

---

## 3. Direct Escape Valve Protocol for UI / Single-Component Tasks

Khi nhận task sửa giao diện (UI / Dashboard / Component ≤ 2 files):
1. **Khảo sát O(1) & Anchor rõ ràng:** Coordinator đọc nhanh file component, xác định chính xác mục tiêu thay thế.
2. **CẤM SPAWN `delegate_task` CHO UI:** Không dùng subagent `ag-gemini-pool-3` để sửa UI vì ngân sách 15 calls không bao giờ đủ cho việc khám phá DOM/CSS.
3. **Sử dụng Claude CLI trực tiếp:** Dispatch qua `python D:/Taadaa/tools/claude_worker.py --role worker` hoặc gọi Claude Code CLI với `--allowedTools Read,Edit,Write,Bash`:
   - Prompt viết trên 1 dòng rõ ràng, mở đầu bằng action verb.
   - Claude Code đọc, viết lại component Master-Detail và chạy kiểm chứng tự động trong 30-60s.
4. **Khởi động lại service & Verify Visual:**
   - Dùng lệnh hệ thống kill PID cũ đang lắng nghe cổng và start lại ngầm (`pythonw`).
   - Kiểm tra `browser_vision` tận mắt để xác nhận giao diện mới đã render chuẩn xác, không bị lẹm viền hay đen màn hình trước khi gửi ảnh cho User.
