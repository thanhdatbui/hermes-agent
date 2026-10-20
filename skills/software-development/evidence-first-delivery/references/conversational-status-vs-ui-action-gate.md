# Phân Biệt Triage Thông Tin vs Thao Tác UI & Chống Bẫy False-Positive Của Gate Nghiệm Thu

## 1. Bối cảnh & Hiện tượng (Sự cố hiển thị Gate 20/10/2026)
Khi User hỏi thông tin tiến độ hoặc tình trạng vận hành ("*Ủa chứ chạy trong bao lâu mà sáng h đc có 26 acc*", "*V có lỗi gì k*"), Coordinator đọc dữ liệu từ log, SQLite và state JSON để giải thích nguyên nhân (ví dụ: ca sáng hoàn tất 30 acc trong 25 phút, 26 thành công, 4 lỗi nghiệp vụ).

Bộ lọc output cũ quét chuỗi văn bản đã kích hoạt **False-Positive nghiêm trọng**:
Tự động bọc khung vi phạm `[EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]` và tuyên bố báo cáo vô giá trị vì thiếu thẻ `MEDIA:<path>`, dù đây là lượt hội thoại thuần túy giải đáp thắc mắc, không hề có bất kỳ thao tác click/tap UI nào.

## 2. Nguyên nhân kỹ thuật gốc (Root Cause)
1. **Khớp từ khóa chuỗi thô (Naive Regex Matching)**:
   Bộ lọc chuỗi quét các cụm từ hành động hoàn thành (`da doi`, `doi thanh`, `thanh cong`, `hoan tat`, `tong ket`, `ket qua`, `da nap`...) đi kèm danh từ (`ten`, `avatar`, `tai khoan`, `may`, `thiet bi`...). Khi Coordinator trả lời bằng ngôn ngữ tự nhiên để tóm tắt số liệu ("kết quả ca", "đăng nhập thành công", "hoàn tất ca"), regex bị kích hoạt mù quáng mà không phân biệt được mục đích của lượt chat.
2. **Xung đột giữa 2 thế hệ kiểm soát**:
   - **Thế hệ mới (Cơ học & Ký số)**: Xác thực dựa trên chữ ký HMAC, thời hạn TTL, đối soát trực tiếp với kết quả trích xuất văn bản từ công cụ thị giác (WinRT OCR / Browser Vision). Kiểm tra diễn ra âm thầm ở tầng trước khi gọi công cụ hoặc trong quy trình xử lý, không làm rác giao diện chat.
   - **Thế hệ cũ (Bọc text thô ở tầng gửi tin)**: Can thiệp trực tiếp vào nội dung trả lời của Agent, chèn thêm cảnh báo làm hoang mang người vận hành và biến một câu trả lời đúng thành báo động giả.

## 3. Quy chuẩn phân loại lượt tương tác (Typed Turn Classification)
BẮT BUỘC phân biệt rạch ròi 2 dạng tương tác:
- **Dạng 1: Live UI / Device Mutation (BẮT BUỘC GATE 6)**:
  + Có hành động thực tế làm biến đổi giao diện/thiết bị: Click, Tap, Điền biểu mẫu, Submit, Đổi màn hình, Đổi thông tin tài khoản.
  + Tuân thủ nghiêm ngặt: Max Blind Steps = 1, chụp ảnh Pre/Post action, soi mắt kiểm tra nội dung và đính kèm `MEDIA:<path>`.
- **Dạng 2: Informational / Triage / Explanatory Turn (MIỄN TRỪ GATE 6)**:
  + Phản hồi câu hỏi khảo sát, giải thích log, truy vấn cơ sở dữ liệu, phân tích lý do watchdog dừng, đối chiếu trạng thái.
  + Toàn bộ turn chỉ dùng công cụ đọc dữ liệu (`read_file`, truy vấn SQLite, đọc state JSON).
  + TUYỆT ĐỐI CẤM kích hoạt cảnh báo thiếu ảnh `MEDIA:` trên dạng turn này.

## 4. Kỷ luật loại bỏ can thiệp chuỗi thô
- Nghiêm cấm mọi cơ chế tự động sửa đổi hoặc chèn tiền tố/hậu tố vào câu trả lời của Agent dựa trên việc quét regex từ khóa hoàn thành.
- Mọi ràng buộc về bằng chứng hình ảnh phải được thực thi ở tầng công cụ thông qua cơ chế kiểm tra tính hợp lệ của token và chữ ký ảnh, yêu cầu Agent điều chỉnh nội bộ thay vì tự tiện thay đổi giao diện trao đổi với User.
