# Cơ chế Auto-Resume Session Sau Khi Restart/Reboot Gateway & PC (26/10/2026)

## 1. Hiện Tượng & Trải Nghiệm Tiêu Cực (User Frustration)
- Mỗi khi PC reboot (restart tay, Windows Update, sập nguồn) hoặc Gateway restart (watchdog, OOM), session đang làm dở khi được khôi phục lại nhảy vào nhắn một câu thụ động:
  > *"Phiên làm việc đã được khôi phục thành công sau khi kết nối gateway hoạt động trở lại. Các tiến trình trước đó đã được ghi nhận. Bạn muốn tiếp tục xử lý nội dung nào tiếp theo?"*
- Người dùng bực mình vì Agent không tự động tiếp tục công việc đang dang dở mà lại dừng lại hỏi xin việc như mất trí nhớ.

## 2. Nguyên Nhân Kỹ Thuật (Root Cause Trong `gateway/run.py`)
1. **Lệch lý do `_reason`:**
   - Trong `gateway/run.py` (trước bản vá 26/10/2026):
     ```python
     _auto_continue_task = (not message) and _reason == "restart_interrupted"
     ```
   - Khi Gateway shutdown/restart bình thường (hoặc Windows gửi tín hiệu shutdown đóng app), `_reason` được đặt là `"restart_timeout"` hoặc `"shutdown_timeout"`.
   - Kết quả: `_auto_continue_task` luôn bị đánh giá là `False`.
2. **System note tiêm lệnh thụ động:**
   - Khi `_auto_continue_task` là `False`, Gateway tiêm vào prompt của LLM:
     ```python
     _resume_guidance = (
         "Report to the user that the session was restored successfully and ask what they would like to do next."
     )
     _replay_guard = (
         "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
     )
     ```
   - Prompt này ép buộc LLM phải bỏ việc đang làm dở, cấm chạy tiếp tool và bắt buộc phải báo khôi phục rồi hỏi user câu hỏi vô nghĩa.

## 3. Kiến Trúc Khép Kín Chuẩn Của Auto-Resume (26/10/2026)

### A. Tầng Khởi Động Windows (Startup Hook)
- File `C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\00_Hermes_AutoResume_Hook.vbs`:
  - Đặt tên với tiền tố `00_` để đảm bảo luôn chạy trước `Hermes_Gateway.vbs`.
  - Gọi `D:\Taadaa\tools\auto_resume_startup_hook.py`.
  - Quét `messages` trong SQLite với `lookback_minutes = 180` (3 giờ) để bao trọn cả các đợt Windows Update kéo dài.
  - Nếu turn cuối của session là `user`, `tool` hoặc `assistant` còn tool calls dở dang: đánh dấu `entry["resume_pending"] = True` và xóa `.clean_shutdown`.

### B. Tầng Điều Phối Gateway (`gateway/run.py`)
- Mở rộng điều kiện nhận diện task tự động chạy tiếp:
  ```python
  _auto_continue_task = (not message) and _reason in (
      "restart_interrupted", "restart_timeout", "shutdown_timeout"
  )
  ```
- Thay toàn bộ prompt thụ động bằng prompt hành động chủ động (Active Continuation):
  ```python
  _resume_guidance = (
      "Kiểm tra lại hiện trường môi trường/thiết bị sau khi "
      "reboot/restart và chủ động tiếp tục thực thi để hoàn thành "
      "dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng "
      "chứng thực tế."
  )
  _replay_guard = (
      "Do NOT replay old tool calls from the history — "
      "re-check the real current state first and issue fresh "
      "calls only for what is still unfinished. NEVER "
      "re-run any reboot/shutdown/restart command. Respect "
      "device locks and any scope limits from the original "
      "task; if state cannot be verified, finish as BLOCKED."
  )
  ```
- Ở cả nhánh fallback (khi synthetic turn rỗng đến từ startup), prompt cũng chỉ đạo:
  > *"Kiểm tra lại hiện trường môi trường/thiết bị sau khi restart và chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng chứng thực tế."*

### C. Quy Tắc Hành Xử Của Agent Sau Khi Khôi Phục
- **Không hỏi xin việc:** Tuyệt đối không chào hỏi hay hỏi "tiếp tục việc gì".
- **Kiểm tra hiện trường thực tế (Fresh Tooling):** Kiểm tra file diff, git log, process ID, ADB device lock xem việc trước khi restart đã hoàn thành đến đâu.
- **Tiếp tục thực thi dứt điểm:** Đi tiếp các bước còn lại đưa task về `DONE` hoặc `BLOCKED` có bằng chứng.
