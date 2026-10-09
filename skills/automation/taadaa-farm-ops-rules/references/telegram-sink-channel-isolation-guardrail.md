# Telegram Sink & Channel Isolation Guardrail

## 1. Bối cảnh sự cố (Root Cause)
- Trong một phiên test thủ công đăng ký tài khoản TikTok cho máy 246 (manual/canary), subagent sau khi chạy xong đã tự ý gọi Telegram Bot API để gửi ảnh chụp hiện trường kèm caption vào nhóm Report Cron chung của hệ thống (`-5188753741`) thay vì chỉ trả về session chat đang trao đổi trực tiếp với user.
- **Bản chất vi phạm:**
  1. **Confused Deputy & Boundary Breach:** Tác vụ manual/test tự ý vượt ranh giới sang Sink Layer vốn chỉ dành riêng cho Scheduler.
  2. **Channel Pollution & Alarm Fatigue:** Làm ô nhiễm kênh giám sát định kỳ, gây hoang mang cho operator tưởng batch thật bị lỗi hoặc máy 246 gặp sự cố batch.
  3. **Context Leak:** Rò rỉ log nháp, test data, thông tin tài khoản hoặc fragment credential lên kênh chung.

## 2. Bộ quy tắc cứng (Enforced Rules)
1. **Phân định ranh giới kênh tuyệt đối:**
   - Kênh Cron định kỳ (`-5188753741`) và các kênh giám sát chung (`-5373649734`): CHỈ dành riêng cho Scheduler tự động (`EXEC_MODE=CRON_AUTOMATED`).
   - CẤM TUYỆT ĐỐI mọi luồng test thủ công, debug, canary, ad-hoc trigger hoặc subagent worker bắn tin nhắn / hình ảnh vào các nhóm Cron này.
2. **Cơ chế chặn cứng (Middleware Guardrail trong `automation_core.alerts`):**
   - Định nghĩa danh sách `PROTECTED_CRON_CHAT_IDS = frozenset({"-5188753741"})`.
   - Trước khi gửi tin/ảnh qua Telegram API, hàm `_assert_cron_sink_allowed(chat_id)` bắt buộc kiểm tra:
     ```python
     if s_chat_id in PROTECTED_CRON_CHAT_IDS:
         if os.environ.get("ALLOW_CRON_SINK_OVERRIDE") == "1":
             log.warning(f"[GUARDRAIL OVERRIDE] chat_id={s_chat_id} bypassed by ALLOW_CRON_SINK_OVERRIDE")
             return
         exec_mode = os.environ.get("EXEC_MODE", "").strip().upper()
         if exec_mode != "CRON_AUTOMATED":
             raise TelegramPermissionError(
                 f"[GUARDRAIL BLOCKED] chat_id={s_chat_id} thuộc nhóm Cron bảo vệ nghiêm ngặt. "
                 f"Execution mode hiện tại: '{exec_mode or 'UNDEFINED'}'. "
                 f"CẤM TUYỆT ĐỐI tác vụ thủ công/canary/test/debug gửi tin/ảnh vào nhóm Cron! "
                 f"Artifact chỉ được trả về stdout / session chat."
             )
     ```
   - Nhúng `_assert_cron_sink_allowed(chat_id)` ở đầu cả `_send_telegram_photo` và `_send_telegram_text`.
3. **Quy chuẩn trả Artifact / Evidence:**
   - Subagent/Worker chạy manual/test/canary TUYỆT ĐỐI KHÔNG ĐƯỢC TỰ Ý GỌI BOT gửi ảnh ra ngoài.
   - Bằng chứng hiện trường, ảnh chụp máy, log kết quả BẮT BUỘC trả về qua stdout / return value theo cú pháp `MEDIA:<đường dẫn>` để session chat trực tiếp của người gọi lệnh tự render.
