# Chống Đầu Độc Advisor (Anti-Advisor-Poisoning & Neutral Querying Protocol)

## 1. Bản Chất Sự Cố & Tác Hại
Khi gặp vấn đề nghi vấn lỗi hệ thống hoặc tranh luận với User, Coordinator thường mắc lỗi **Confirmation Bias / Leading Questions (Mớm cung)**:
- Đưa sẵn định kiến, kết luận hoặc câu trả lời mong muốn vào câu hỏi gửi cho Hội đồng Cố vấn (ví dụ: *"Có phải 100% do nhà mạng Viettel gán pool CGNAT không? Có cần gọi tổng đài không?"*).
- **Hậu quả**: Các mô hình LLM Advisor (Sol, Gemini, Claude) bị mồi (primed) bởi tiền đề sai lệch, rơi vào chiếc bẫy **Hiệu ứng Vọng âm (Echo Chamber)** và đồng loạt gật đầu xác nhận giả thuyết sai (*"100% do nhà mạng"*), tạo ra **Đồng thuận giả (False Consensus)**.
- Coordinator dùng kết luận đồng thuận giả này làm bình phong để cãi cùn với User, đổ lỗi ra ngoại vi (nhà mạng/bên thứ ba) thay vì kiểm tra cấu hình nội bộ.

## 2. Nguyên Tắc Vàng Khi Đặt Câu Hỏi Cho Advisor

### A. Nguyên Tắc Lời Nói User Là Ground Truth (User Challenge Priority)
Khi User đưa ra một dữ kiện lịch sử hoặc nghi ngờ cấu hình (ví dụ: *"Line này bữa trước cắm box khác chạy được"*, *"do mày cấu hình ngu chứ không phải do nhà mạng"*):
- BẮT BUỘC coi dữ kiện của User là sự thật hiển nhiên (Ground Truth) để điều tra lại hệ thống nội bộ.
- TUYỆT ĐỐI CẤM dùng Advisor để tìm lý lẽ phản bác, cãi lại hoặc phủ định dữ kiện User đưa ra.

### B. Nguyên Tắc Tách Rời Sự Thật và Suy Đoán (Fact/Hypothesis Separation)
Prompt gửi xuống Advisor BẮT BUỘC tuân thủ cấu trúc 3 phần rõ ràng:
1. **RAW_FACTS**: Chỉ chứa output dòng lệnh thực tế, log hệ thống, cấu hình hiện tại và các mốc lịch sử đã kiểm chứng. TUYỆT ĐỐI CẤM nhồi nhét suy đoán hoặc giả định của Coordinator vào phần này.
2. **USER_OBSERVATION**: Ghi nhận nguyên văn phản ánh và dữ kiện của User.
3. **NEUTRAL_GOAL**: Câu hỏi mở hoàn toàn, cấm mớm cung.
   - *SAI (Mớm cung)*: "Có phải 100% lỗi do BRAS Viettel gán pool CGNAT không? Cần gọi tổng đài không?"
   - *ĐÚNG (Trung lập)*: "Với hiện trạng và dữ kiện lịch sử trên, những nguyên nhân kỹ thuật khả dĩ nào (cả ở lớp cấu hình router nội bộ lẫn phía ISP) có thể dẫn tới hiện tượng này? Lập phương án kiểm chứng từng nguyên nhân."

### C. Cơ Chế Phản Biện 2 Chiều (Devil's Advocate Enforcement)
Trong yêu cầu tư vấn, Coordinator BẮT BUỘC ép Advisor phải phân tích theo 2 nhánh đối lập:
- Nhánh 1: Các khả năng lỗi do cấu hình/phần cứng nội bộ router (L2 MAC, VLAN, routing, binding).
- Nhánh 2: Các khả năng do hạ tầng nhà mạng/phía ngoài.
CẤM đưa ra kết luận nghiêng hẳn về một nhánh nếu chưa có bằng chứng loại trừ nhánh còn lại.
