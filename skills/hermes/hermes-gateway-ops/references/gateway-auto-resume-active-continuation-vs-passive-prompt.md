# Gateway Auto-Resume Active Continuation vs Passive Question Prompt

## 1. Hiện Tượng Thực Tế
- Mỗi khi Gateway restart hoặc PC reboot/crash trong lúc Agent đang làm dở task, khi session được khôi phục, Agent không tự động làm tiếp công việc mà luôn dừng lại và gửi một tin nhắn thụ động giống hệt nhau ở mọi session:
  > *"Phiên làm việc đã được khôi phục thành công sau khi kết nối gateway hoạt động trở lại. Các tiến trình trước đó đã được ghi nhận. Bạn muốn tiếp tục xử lý nội dung nào tiếp theo?"*
- Người dùng bức xúc vì Agent "mất não", bỏ dở công việc đang chạy và hỏi xin việc lại từ đầu.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Phân nhánh `_auto_continue_task` bị trói cứng:**
   - Trong `gateway/run.py` (dòng ~19081):
     ```python
     _auto_continue_task = (not message) and _reason == "restart_interrupted"
     ```
   - Khi Gateway restart thông thường (do watchdog, memory drain, hoặc crash shutdown), `_reason` luôn là `"restart_timeout"` hoặc `"shutdown_timeout"`.
   - Kết quả: `_auto_continue_task` bị đánh giá là `False`.
2. **System Prompt ép LLM dừng lại và hỏi:**
   - Khi `_auto_continue_task` là `False`, Gateway rơi vào nhánh `else` và tiêm thẳng System Note vào prompt của LLM:
     ```python
     _resume_guidance = (
         "Report to the user that the session was restored successfully and ask what they would like to do next."
     )
     _replay_guard = (
         "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
     )
     ```
   - Nhánh fallback an toàn (dòng ~19178) cũng tiêm: *"Report to the user that the session was restored successfully and ask what they would like to do next. Do NOT re-execute old tool calls — skip any unfinished work..."*
   - LLM đọc thấy mệnh lệnh hệ thống cấm chạy tiếp và bắt buộc phải báo cáo thành công rồi hỏi User ➡️ biến thành hành vi thụ động.

## 3. Kiến Trúc Khép Kín Auto-Resume Khi Reset PC / Gateway Restart

### A. Tầng Windows Boot (Startup Hook)
- File `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\00_Hermes_AutoResume_Hook.vbs`:
  - Đặt tiền tố `00_` để đảm bảo chạy trước `Hermes_Gateway.vbs`.
  - Gọi `D:\Taadaa\tools\auto_resume_startup_hook.py` với `lookback_minutes=180` (3 giờ để bao phủ cả trường hợp Windows Update lâu).
  - Quét `messages` trong SessionDB: nếu tin nhắn cuối cùng là `user`, `tool` hoặc `assistant` còn `tool_calls` dở dang ➡️ đánh dấu `resume_pending = True`, `resume_reason = "restart_interrupted"`, và xóa file `.clean_shutdown`.

### B. Tầng Gateway Dispatch (`gateway/run.py`)
- Mở rộng điều kiện nhận diện task tự động tiếp tục:
  ```python
  _auto_continue_task = (not message) and _reason in (
      "restart_interrupted", "restart_timeout", "shutdown_timeout"
  )
  ```
- Thay thế triệt để các prompt thụ động bằng chỉ thị chủ động thực thi:
  ```python
  elif _auto_continue_task:
      _resume_guidance = (
          "Kiểm tra lại hiện trường môi trường/thiết bị sau khi reboot/restart và "
          "chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED "
          "kèm bằng chứng thực tế."
      )
  ```
  Và trong `_replay_guard`:
  ```python
  _replay_guard = (
      "Do NOT replay old tool calls from the history — re-check the real current state first "
      "and issue fresh calls only for what is still unfinished. NEVER re-run any reboot/shutdown/restart command. "
      "Respect device locks and any scope limits from the original task; if state cannot be verified, finish as BLOCKED."
  )
  ```

## 4. Kiểm Thử & Nghiệm Thu
- Chạy `python D:/Taadaa/tools/auto_resume_startup_hook.py` độc lập xác nhận bảo toàn thành công các session in-flight.
- Chạy `pytest tests/gateway/` xác nhận không làm vỡ các luồng gateway session.
