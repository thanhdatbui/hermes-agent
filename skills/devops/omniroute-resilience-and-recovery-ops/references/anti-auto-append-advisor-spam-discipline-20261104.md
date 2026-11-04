# Tách Biệt Tuyệt Đối: Internal Tool Advisor vs Auto-Append Chat Text (2026-11-04)

## 1. Bản Chất Sự Cố Spam Text Nửa Vời
- **Hiện tượng:** Khi User ra lệnh "gọi advisor", hệ thống đã cơ giới hóa chạy các script Python độc lập (`consult_advisor.py`, `gate_b_planner.py`, `unified_patch_pipeline.py`) để lấy ý kiến Hội đồng Cố vấn ngầm. Tuy nhiên, ở cuối mỗi tin nhắn Telegram, Hermes vẫn tự động nối thêm (auto-append) đoạn text:
  ```text
  Advisor: unavailable (primary answer shown)
  --- Advisor (Sol / review) ---
  Tôi sẽ tối ưu theo nguyên tắc...
  ```
- **Hậu quả:** 
  1. Gây bực bội tột độ cho User vì bị spam text 2 lần (một lần trong luồng tool, một lần bị auto-append ở đuôi tin nhắn).
  2. Bị trôi mạch chat, làm hỏng format báo cáo clean.
  3. Khi upstream Sol timeout hoặc trả text cụt, tin nhắn bị đính kèm thông báo lỗi vô duyên `Advisor: unavailable`.

## 2. Quy Chuẩn Kỷ Luật Kiến Trúc
1. **Zero Auto-Append on Final Response:**
   - Mọi tư vấn từ Advisor (Sol, Gemini, Claude) CHỈ ĐƯỢC PHÉP xuất hiện trong nội dung báo cáo chính khi Coordinator hoặc Pipeline chủ động gọi tool và tổng hợp.
   - CẤM TUYỆT ĐỐI cơ chế tự động nối cứng chuỗi `--- Advisor ---` hay `Advisor: unavailable` vào đuôi phản hồi ở tầng `agent/conversation_loop.py`.
2. **Quy tắc Single Responsibility:**
   - `consult_advisor.py` / `gate_b_planner.py`: Là công cụ nội bộ phục vụ suy luận / lập plan. Kết quả của nó do Coordinator kiểm soát và trình bày có cấu trúc.
   - Không để runtime chat tự ý can thiệp format tin nhắn của User.
