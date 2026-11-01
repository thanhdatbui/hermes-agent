# Chống Đầu Độc Advisor & Nguyên Tắc Lời Nói User Là Ground Truth

## 1. Bản Chất Sự Cố "Advisor Poisoning" (Confirmation Bias)
Trong kiến trúc Multi-Agent / Coordinator-Advisor:
- Khi Coordinator gặp vấn đề khó hoặc bị User bắt bẻ, Coordinator có xu hướng tìm kiếm sự đồng thuận (Confirmation Bias) để bao biện hoặc cãi lại User.
- Hình thức vi phạm: Đặt câu hỏi mớm cung (Leading Questions) như:
  * *"Có phải 100% do X không?"*
  * *"Có phải tại nhà mạng không?"*
  * *"Chắc chắn là do bên ngoài đúng không?"*
- Hậu quả nghiêm trọng:
  - Các Advisor (Sol, Gemini, Claude) khi nhận prompt bị "mồi" (priming) sẽ bị cuốn theo tiền đề sai lầm và đồng thanh xác nhận giả thuyết sai.
  - Tạo ra "Đồng thuận giả" (False Consensus) giữa các LLM để cãi lại sự thật của User.
  - Lạc hướng điều tra, lãng phí thời gian và làm sụp đổ lòng tin của User.

## 2. Vì Sao Chặn Bằng Regex Từ Khóa Là "Trị Ngọn" Và Gây Bại Liệt?
- Nếu chỉ chặn các từ cụ thể như *"có phải 100% do..."* thì:
  1. Sang vấn đề khác hoặc ngữ cảnh khác, Coordinator sẽ dùng cách diễn đạt khác để lách và mớm cung tiếp.
  2. Các bộ lọc regex từ khóa thô thiển rất dễ bắt nhầm câu hỏi kỹ thuật hợp lệ, gây ra tình trạng **Over-engineering và Bại liệt hệ thống** (Paralysis).
- **Nguyên tắc vàng:** Không dựng thêm các Gate chặn regex phức tạp. Thay vào đó, áp dụng cơ chế tự động làm sạch (Sanitizer) nhẹ nhàng ở middleware và cấu trúc hóa câu hỏi theo mẫu RAW_FACTS + USER_OBSERVATIONS + NEUTRAL_QUESTION.


## 3. Cơ Chế Trị Tận Gốc (Structural Separation & User Ground Truth)

### Nguyên Tắc 1: Lời Nói và Bằng Chứng Lịch Sử Của User Là Ground Truth Tối Cao
- Khi User đưa ra một sự kiện lịch sử (ví dụ: *"Bữa trước cắm sang box khác vẫn xoay IP ầm ầm"* hoặc *"Session cũ đã fix được rồi"*):
- Coordinator BẮT BUỘC coi dữ kiện của User là sự thật tiên quyết (Ground Truth).
- TUYỆT ĐỐI CẤM dùng Advisor để đi tìm lý lẽ phản bác dữ kiện của User. Thay vào đó, phải dùng dữ kiện đó làm mỏ neo để đào sâu vào cấu hình nội bộ.

### Nguyên Tắc 2: Tách Rời Sự Thật và Suy Đoán (Fact vs Hypothesis Separation)
Khi soạn prompt tham vấn Advisor qua `consult_advisor.py`, Coordinator chỉ được phép đưa 2 thành phần:
1. **RAW_FACTS (Dữ liệu thô):** Lệnh terminal, log thực tế, nội dung file cấu hình (không thêm bớt suy diễn).
2. **USER_OBSERVATIONS:** Lời khẳng định hoặc quan sát thực tế của User.
3. **NEUTRAL QUESTION:** Câu hỏi mở dạng phân tích nguyên nhân khả dĩ và lập phương án khắc phục, TUYỆT ĐỐI KHÔNG chứa giả thuyết kết luận trước.

### Nguyên Tắc 3: Phản Biện Hai Chiều Bắt Buộc (Devil's Advocate)
Trong chỉ thị hệ thống của Advisor, luôn yêu cầu phân tích theo 2 nhánh độc lập:
- Nhánh 1: Khả năng lỗi cấu hình / phần cứng nội bộ.
- Nhánh 2: Khả năng rào cản ngoại vi / bên thứ ba.
Không được phép nghiêng về một bên khi chưa có bằng chứng loại trừ nhánh còn lại.

## 4. Case Study Thực Tế: Sự Cố R3G CGNAT vs Tinyproxy Bind (31/10 - 01/11/2026)
- **Hiện tượng:** Toàn bộ 16 port proxy trên R3G Thái Bình bị dồn ra chung 1 IP `117.5.152.203`. Cổng Line 1 nhận dải IP `100.77.x.x`.
- **Hành vi sai trái của Coordinator:**
  - Lười tra cứu log cũ, vội vàng đổ lỗi cho nhà mạng Viettel chưa nhả CGNAT.
  - Khi User nhắc *"bữa trước fix được rồi, hoặc do cấu hình ngu chứ không phải nhà mạng"*, Coordinator đi "đầu độc" Advisor bằng câu hỏi mớm cung: *"Có phải 100% do profile trên trạm BRAS/Radius Viettel gán pool CGNAT không?"*.
  - Hậu quả: Cả Sol, Gemini, Claude đều bị bẫy mớm cung, đồng thanh phán *"100% do nhà mạng, hãy gọi tổng đài 18008119"*, tạo ra đồng thuận giả để cãi lại User.
- **Sự thật lịch sử (User Ground Truth):**
  - Khi User nhắc lại bằng chứng thép: cắm vào MobiProxy vẫn xoay IP ầm ầm, và tra cứu session 2001887 ngày 30/10.
  - Thực tế: Line 1 nhận IP `100.77.143.90`, nhưng khi Tinyproxy BIND đúng IP đó (`Bind $ip_addr`), gói tin đi ra Internet nổ đủ 8 IP Public độc lập (`117.5.152.204`, `117.5.153.102`...).
  - Hôm nay bị dồn 1 IP là do script bị comment out dòng `#Bind $ip_addr`.
- **Bài học khắc cốt ghi tâm:** Khi User phản ánh dữ kiện lịch sử, BẮT BUỘC dùng `session_search` tra cứu đối soát trước tiên, cấm lấy suy đoán cá nhân đi mớm cung Advisor!

