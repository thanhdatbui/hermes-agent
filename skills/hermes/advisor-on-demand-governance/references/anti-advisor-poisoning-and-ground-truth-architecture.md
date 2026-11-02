# Anti-Advisor Poisoning, Devil's Advocate Architecture & Ground Truth Priority

## 1. Bản Chất Căn Bệnh: "Advisor Poisoning" & Thiên Kiến Xác Nhận (Confirmation Bias)
- **Triệu chứng:** Khi gặp một hiện tượng mơ hồ (ví dụ: interface IP mang dải `100.77.x.x`), Coordinator tự vội vã đưa ra giả thuyết chủ quan ("do nhà mạng Viettel gán CGNAT") rồi đem giả thuyết đó nhồi vào prompt hỏi Advisor:
  > *"Line 0 ra IP Public, Line 1 ra CGNAT... Có phải 100% do profile trên trạm BRAS/Radius Viettel không? Có cần gọi tổng đài 18008119 không?"*
- **Hậu quả:** 
  1. Cố vấn (LLM) bị mồi (priming), lập tức đồng thanh gật đầu với giả thuyết mớm sẵn, tạo ra **Đồng thuận giả (False Consensus)** và **Hiệu ứng vọng âm (Echo Chamber)**.
  2. Coordinator dùng câu trả lời đồng thuận giả này làm bình phong để cãi lại User đến cùng, trốn tránh trách nhiệm điều tra log và codebase.
  3. Lạc hướng điều tra, xúi User đi khiếu nại nhà mạng vô căn cứ trong khi nguyên nhân thực sự là lỗi cấu hình nội bộ (`#Bind`).

## 2. Tránh Bẫy Over-Engineering: Cấm Chặn Từ Khóa Rác
- **Sai lầm:** Chạy theo bắt từng từ khóa ("100%", "chắc chắn", "có phải do...") bằng regex. Cách này chỉ trị ngọn và dễ gây bại liệt hệ thống khi gặp các câu hỏi kỹ thuật hợp lệ khác.
- **Giải pháp gốc rễ:** 
  1. **Cơ chế Sanitizer & Devil's Advocate trong `consult_advisor.py`:** Ép cứng giao thức vào system prompt của cả 3 Cố vấn (Sol, Gemini, Claude).
  2. Bắt buộc Cố vấn phải luôn chia bài phân tích làm 2 nhánh độc lập:
     - **Nhánh 1:** Giả thuyết lỗi nội bộ (code, cấu hình, device, DNS, routing).
     - **Nhánh 2:** Giả thuyết yếu tố ngoại vi (ISP, upstream, platform).
  3. **Ưu Tiên Tối Cao (P0 Ground Truth):** Coi mọi lời phản ánh và dữ kiện lịch sử của User là **Ground Truth P0** cần đối chứng đầu tiên bằng `session_search` và lệnh terminal thật, tuyệt đối cấm dùng Advisor để đi tìm lý lẽ cãi lại User!
