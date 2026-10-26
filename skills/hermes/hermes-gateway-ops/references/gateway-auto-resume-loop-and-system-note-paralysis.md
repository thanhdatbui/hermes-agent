# Gateway Auto-Resume Behavior & System Note Paralysis (26/10/2026)

## 1. Hiện Tượng (Symptom)
- Khi Gateway khởi động lại (restart do memory watchdog, drain timeout, hoặc reload service), các session bị ngắt quãng giữa chừng được tự động khôi phục.
- Thay vì tiếp tục hoàn thành công việc dang dở, Coordinator/Agent lại gửi tin nhắn mặc định mang tính thụ động, đóng băng:
  > *"Phiên làm việc đã được khôi phục thành công sau khi kết nối gateway hoạt động trở lại. Các tiến trình trước đó đã được ghi nhận. Bạn muốn tiếp tục xử lý nội dung nào tiếp theo?"*
- Người dùng bức xúc vì Agent dừng lại hỏi thay vì chủ động làm tiếp.

## 2. Nguyên Nhân Gốc Rễ Trong Code Gateway (`gateway/run.py`)
1. **Phân loại lý do ngắt quãng (`_reason`):**
   - Khi Gateway restart (ví dụ qua lệnh restart, drain timeout), Gateway đánh dấu session với `resume_pending = True` và:
     ```python
     _resume_reason = "restart_timeout" if self._restart_requested else "shutdown_timeout"
     ```
2. **Điều kiện `_auto_continue_task` bị bó hẹp sai:**
   - Trong `gateway/run.py` (dòng ~19081):
     ```python
     _auto_continue_task = (not message) and _reason == "restart_interrupted"
     ```
   - Giá trị `"restart_interrupted"` chỉ được gán trong script PC reboot (`farm_preflight_daily_reset.py`).
   - Mọi trường hợp restart Gateway thông thường đều có `_reason == "restart_timeout"` hoặc `"shutdown_timeout"`, dẫn đến `_auto_continue_task = False`.
3. **Tiêm Prompt Ép Dừng Công Việc (System Note Paralysis):**
   - Khi `_auto_continue_task = False`, Gateway tự động tiêm chỉ thị sau vào prompt của LLM:
     ```python
     _resume_guidance = (
         "Report to the user that the session was restored successfully and ask what they would like to do next."
     )
     _replay_guard = (
         "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
     )
     ```
   - LLM tuân thủ tuyệt đối chỉ thị hệ thống này: bỏ qua công việc đang làm dở, cấm chạy tiếp tool, dịch câu thông báo sang tiếng Việt và hỏi người dùng.

## 3. Giải Pháp & Quy Tắc Khắc Phục (Invariant)
1. **Mở Rộng Điều Kiện Auto-Continue Trong `gateway/run.py`:**
   - Cần cho phép mọi lý do restart/shutdown timeout đều kích hoạt `_auto_continue_task`:
     ```python
     _auto_continue_task = (not message) and _reason in (
         "restart_interrupted", "restart_timeout", "shutdown_timeout"
     )
     ```
2. **Thay Đổi Nội Dung System Note Hướng Dẫn:**
   - Thay vì *"Report to the user and ask what to do next... skip any unfinished work"*, chỉ thị hệ thống phải là:
     > *"Kiểm tra lại hiện trường môi trường/thiết bị sau khi restart và chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng chứng thực tế. Không hỏi lại những điều đã rõ."*
3. **Kỷ Luật Tác Vụ Của Coordinator Khi Nhận Turn Resume:**
   - Dù Gateway có tiêm câu nhắc resume nào, Coordinator BẮT BUỘC tuân thủ **Invariant Thang Điều Phối Tích Cực**:
     * TUYỆT ĐỐI CẤM dừng lại hỏi khách sáo kiểu "bạn muốn làm gì tiếp theo".
     * Lập tức gọi `git status` hoặc `inspect_machine` kiểm tra trạng thái lệnh trước đó.
     * Tiếp tục thực thi nhánh việc dở dang cho tới khi đạt `DONE` hoặc `BLOCKED` có bằng chứng.
