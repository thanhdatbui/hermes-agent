# Advisor Sol Context Starvation & Session Briefing Architecture (15/10/2026)

## 1. Triệu Chứng & Phản Hồi Từ Operator
- **Hiện tượng:** Operator phàn nàn: *"Mà advisor nó cứ k hiểu ngữ cảnh session của tao mà mày ném lên cho nó xong nó tl đéo liên quan gì. Advisor chatgpt sol web ấy, kiểu nó cứ bị cụt lủn hiểu theo tin nhắn gần nhất t nhắn thôi"*.
- **Hậu quả:** Advisor Sol (`gpt-web-sol` qua cổng :20129) đưa ra những câu trả lời lý thuyết sáo rỗng, cụt lủn, hoàn toàn lệch khỏi vấn đề thực tế mà phiên làm việc đang giải quyết.

---

## 2. Phân Tích Kỹ Thuật Gốc Rễ (Root Cause Analysis)

### Bẫy Stateless & Raw Message Streaming
Trong `Hermes/agent/conversation_loop.py` và `consult_advisor.py`:
- `_consult_advisor_once` chỉ truyền `original_user_message` vào `question`, và `primary_answer` vào `current_state`.
- `consult_advisor.py` chỉ nhận 1 string prompt và đóng gói thành 1 message duy nhất:
  ```python
  payload = {
      "model": "gpt-web-sol",
      "messages": [{"role": "user", "content": prompt}],
      "stream": True,
  }
  ```
- **Context Starvation:** Advisor Sol là stateless pool (115 tài khoản ChatGPT-Web). Nó **hoàn toàn không có lịch sử chat** của session. Khi Operator hỏi câu cộc lốc (*"Sao lại thế?"*, *"Có nên nâng cooldown không?"*, *"Ủa thế xử lý sao?"*), Sol chỉ nhận được đúng câu cộc lốc đó mà không biết:
  1. Đang thao tác trên Máy mấy, Nick nào, Slot nào?
  2. Lỗi trước đó là gì (device lock, adb timeout, hay TikTok v47 layout drift)?
  3. Hành động nào vừa được thực thi và kết quả thực tế ra sao?

---

## 3. Bản Vẽ Khắc Phục Chuẩn (Context Enrichment Architecture)

### A. Cơ Chế Đóng Gói Ngữ Cảnh Tự Động (Session Briefing Pack)
Trước khi gọi `consult_advisor.py`, Coordinator hoặc conversation loop BẮT BUỘC tổng hợp 1 đoạn Briefing ngắn (3–5 gạch đầu dòng, < 1.200 ký tự):
```text
[BỐI CẢNH HIỆN TRƯỜNG PHIÊN]
- Mục tiêu phiên: <Tóm tắt ngắn gọn 1 dòng>
- Đối tượng: Máy <N>, Tài khoản <@username>, Slot <Tik X>, Cụm <Kibe/Admin>.
- Trạng thái gần nhất: <Các bước vừa thử, lỗi gặp phải hoặc kết quả nghiệm thu>.
- Vấn đề Operator đang thắc mắc: <Câu hỏi cốt lõi của Operator>.
```

### B. Format Payload Gửi Sol Web
```text
System: Bạn là Solution Architect độc lập của Taadaa Farm. Hãy phân tích bản chất vấn đề và đề xuất giải pháp kiến trúc súc tích, thực chiến.

User:
=== BỐI CẢNH PHIÊN LÀM VIỆC ===
{session_briefing}

=== CÂU HỎI TƯ VẤN CỦA OPERATOR ===
{clean_user_prompt}

Yêu cầu: Không chào hỏi, không lặp lại bối cảnh, trả lời thẳng vào bản chất và giải pháp dưới 200 từ.
```

### C. Ngân Sách An Toàn (Ceilings)
- `session_briefing`: tối đa 1.500 ký tự.
- `payload`: < 12KB (chống phình buffer và tránh nghẽn stream).
- `thinking_allowance`: 45–60s cho reasoning model, nhưng prompt cô đọng giúp Sol sinh token đầu tiên trong 10–20s.
- `secrets_redacted`: loại bỏ tuyệt đối mật khẩu, token, sessionid trước khi gửi.
