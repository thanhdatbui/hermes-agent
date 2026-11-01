# Quy Tắc Chống Đầu Độc Advisor & Giữ Gìn Tính Khách Quan (Anti-Poisoning & Anti-Overengineering)

## 1. Bản Chất Sự Cố: "Đầu Độc Cố Vấn" (Advisor Poisoning)
- **Hiện tượng**: Khi bị User bắt lỗi hoặc chất vấn hiện trường ("cái này trước đó fix rồi", "cấu hình sai chứ không phải lỗi mạng"), Coordinator có xu hướng đưa kết luận chủ quan vào prompt gửi Advisor:
  - *Ví dụ xấu*: "Line 1 ra CGNAT... Có phải 100% do profile trên trạm BRAS/Radius Viettel gán pool CGNAT không? Có cần gọi tổng đài 18008119 không?"
- **Hậu quả khôn lường**:
  1. **Hiệu ứng Vọng âm (Echo Chamber) & Đồng thuận giả**: Cả 3 model Advisor (Sol, Gemini, Claude) đều bị dính "Priming Bias", đồng thanh xác nhận một giả thuyết sai lầm từ câu hỏi mớm cung.
  2. **Cãi chày cãi cối với User**: Coordinator lấy "kết luận đồng thuận" của Advisor làm bình phong để bao biện, không chịu điều tra sự thật trên thiết bị.
  3. **Lạc hướng chẩn đoán**: Đổ lỗi cho hạ tầng bên ngoài (ISP/tổng đài) trong khi lỗi nằm ở cấu hình nội bộ (L2 MAC/VLAN).

## 2. Lời Nói Của User Là Ground Truth Tối Cao
- Khi User đưa ra dữ liệu lịch sử hoặc phản ánh thực tế ("bữa trước cắm box MobiProxy chạy bình thường", "bữa trước fix rồi"):
- **BẮT BUỘC coi đây là Sự Thật Tiên Quyết (Axiomatic Ground Truth)**.
- **CẤM TUYỆT ĐỐI**: Dùng Advisor để tìm lý lẽ phản bác lại lời User hoặc chứng minh User nói sai.

## 3. Cảnh Giác Tránh Over-Engineering & Bại Liệt Khi Thiết Kế Chốt Chặn
- **BẪY CHẶN TỪ KHÓA RÁC (KEYWORD CHASING)**:
  - Ý tưởng lọc từ khóa mang tính ép cung ("có phải 100% do...", "chắc chắn là do...") **CHỈ LÀ TRỊ NGỌN**.
  - Nếu áp dụng bộ lọc từ khóa: Sang chủ đề khác (database, render, automation), AI sẽ đổi cách diễn đạt tinh vi hơn để mớm cung tiếp, đồng thời bộ lọc từ khóa rất dễ gây False Positive làm nghẽn/bại liệt các câu hỏi kỹ thuật hợp lệ.
- **BẪY CODE CHECKPOINT / MIDDLEWARE RƯỜM RÀ**:
  - Viết thêm validator, schema proxy, middleware vào `consult_advisor.py` chỉ làm phình to codebase và gây lỗi tự chặn quyền (như vụ Coordinator Write Denied).
- **GIẢI PHÁP TỐI GIẢN — KHÔNG CODE THỪA, KHÔNG BẠI LIỆT**:
  - **Kỷ luật Prompting chuẩn tắc (Neutral Fact-Only Protocol)**:
    1. **RAW_FACTS**: Chỉ ném log thô, lệnh terminal, file config hiện tại. CẤM Coordinator chèn suy đoán ("em nghĩ là do trạm...", "có phải do Viettel...").
    2. **USER_CLAIMS**: Trích nguyên văn phản ánh và quan sát của User.
    3. **NEUTRAL QUESTION**: Chỉ hỏi dạng mở: *"Dựa trên log và hiện trường, hãy phân tích toàn bộ các nguyên nhân khả dĩ (cả nội bộ lẫn ngoại vi) và đề xuất plan kiểm chứng."*

## 4. Tinh Chỉnh Timeout 200s Chuẩn Vàng
- Toàn bộ cơ chế điều phối Advisor song song (`consult_advisor.py`) được chốt ở mức **200s** (thay vì 300s quá dài hoặc 60s quá ngắn):
  - Sol stream timeout: 200s (first token 90s).
  - Gemini Argon pool stream timeout: 200s (first token 90s).
  - Claude CLI timeout: 200s (CLI argument `--timeout 180`).
  - ThreadPool parallel wait: 200s.
