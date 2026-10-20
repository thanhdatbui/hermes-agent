# Chuyển Đổi Advisor Sang Cơ Chế On-Demand & Nâng Cấp Streaming Đa Tầng (2026-10-20)

## 1. Bối Cảnh & Triệu Chứng Lỗi
- **Triệu chứng:** Operator phản ánh: *"nên tiếp tục xài guard advisor không, nó cứ thiếu ngữ cảnh nói chuyện như ngáo ngáo vậy? Hay là khi cần tao mới chat gọi"*.
- **Hiện trường thực tế:** Khi Operator và Coordinator đang bàn luận kỹ thuật (ví dụ cấu hình proxy SOCKS5, Singbox, điều phối Claude), cơ chế `auto-append` tự động kích hoạt Advisor Sol ở cuối turn. Do bộ đệm context trước đây bị bóp quá ngắn (`MAX_MSG_CHARS = 280`, `MAX_BRIEF_CHARS = 1500`), toàn bộ nội dung kỹ thuật sâu bị cắt cụt, chỉ còn sót lại cụm từ cộc lốc *"thống nhất với Claude"*.
- **Hậu quả:** Advisor Sol (ChatGPT-Web pool stateless) phản xạ phòng thủ: *"Tao không thể tự nhận đã thống nhất với Claude nếu trong cuộc trò chuyện này chưa có nội dung trao đổi đó. Mày gửi cho tao đoạn hội thoại hoặc bản thống nhất..."*, gây đứt gãy mạch đàm thoại và làm phiền Operator.

---

## 2. Phân Tích Kỹ Thuật Gốc Rễ

1. **Bẫy Auto-Append trên Stateless Web Pool:**
   - Việc tự động bắt từ khóa tư vấn (`nên`, `được không`, `thấy sao`...) và tự động gắn đuôi Advisor Sol vào mọi câu trả lời làm phát sinh 3 vấn đề lớn:
     - Độ trễ phản hồi trên Telegram tăng thêm 45–60 giây cho mỗi tin nhắn bình thường.
     - Đói ngữ cảnh (Context Starvation) hoặc Attention Drift (lạc trôi sự chú ý vì gom nhầm các mẩu tin nhắn cũ không liên quan).
     - Sol bắt bẻ câu chữ do không nhận được toàn văn đề tài.
2. **Bẫy Timeout 55s với `stream: False` trong `advisor_tool.py`:**
   - Trong `Hermes/tools/advisor_tool.py`, request gửi sang OmniRoute cổng :20129 trước đây đặt `stream: False` và `DEFAULT_TIMEOUT = 55`.
   - Với reasoning model (`gpt-web-sol`), khi nhận prompt dài giàu ngữ cảnh, thời gian TTFT suy nghĩ ngầm vọt lên 40s–60s. Không có keepalive stream khiến socket bị drop ngắt ở mốc 55s (`TimeoutError`), buộc code phải hạ context xuống 280 ký tự để né timeout.

---

## 3. Kiến Trúc Khắc Phục Chuẩn Hóa

### A. Chuyển Dứt Điểm Sang On-Demand (Chỉ Gọi Khi Operator Yêu Cầu)
- Trong `agent/conversation_loop.py`, thay thế việc nhận diện regex tư vấn tràn lan bằng danh sách trigger chủ động rõ ràng:
  ```python
  _ADVISOR_EXPLICIT_TRIGGERS = (
      "gọi advisor",
      "hỏi sol",
      "gọi sol",
      "sol thấy sao",
      "nhờ sol review",
      "sol lên plan",
  )
  ```
- Các câu hỏi tư vấn thông thường trong phiên (`nên chọn A hay B`, `làm thế nào...`) sẽ do Coordinator trả lời trực tiếp, không tự động gọi Sol chen ngang.

### B. Nâng Trần Bối Cảnh Trong `advisor_context.py`
- Tăng giới hạn để giữ trọn vẹn ý đồ và chi tiết kỹ thuật của từng turn:
  - `MAX_MSG_CHARS = 800` (thay vì 280).
  - `MAX_BRIEF_CHARS = 4000` (thay vì 1500).
  - Giữ `MAX_TURNS = 5`.

### C. Nâng Cấp Streaming SSE & Bỏ Trần Timeout 55s Trong `advisor_tool.py`
- Chuyển `payload["stream"] = True`.
- Cấu hình trần thời gian 3 tầng tương thích reasoning model:
  - `FIRST_TOKEN_TIMEOUT = 80s`: cho phép Sol có đủ thời gian reasoning sâu.
  - `IDLE_TOKEN_TIMEOUT = 20s`: kiểm tra khoảng lặng giữa các chunk SSE.
  - `DEFAULT_TIMEOUT = 140s`: trần an toàn tổng thể cho toàn bộ câu trả lời.
- Đồng bộ cấu hình OmniRoute (:20129) tại `.env`:
  - `STREAM_READINESS_TIMEOUT_MS = 80000` (80s).
  - `ACCOUNT_SEMAPHORE_TIMEOUT_MS = 90000` (90s).
