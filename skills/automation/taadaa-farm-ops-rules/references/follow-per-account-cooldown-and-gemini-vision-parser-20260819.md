# BÀI HỌC VẬN HÀNH: COOLDOWN NHẢ FOLLOW THEO NICK & SỬA PARSER GEMINI VISION AUTO-RECOVERY (19/08/2026)

## 1. Cơ Chế Cách Ly Nhả Follow Theo Từng Nick Riêng Biệt (Per-Account Row Cooldown)
- **Bản chất hiện tượng**: Dữ liệu thực tế 19/08 trên 42 máy chạy cả Row 1 và Row 3 cho thấy có tới 15 máy mà Row 1 follow thành công rực rỡ (3-8 lượt), nhưng sang Row 3 trên cùng máy đó lại bị nhả follow. Điều này chứng minh 100% việc nhả follow phụ thuộc vào **độ trust của từng tài khoản TikTok**, không phải do máy hay IP.
- **Quy tắc cô lập**:
  - State file chuyển sang quản lý theo từng account row: `follow_state_{machine}_row_{account_row_index}.json`.
  - Khi Nick ở Row X bị nhả follow sau khi vuốt kiểm tra (`pull-to-refresh`):
    - Đánh dấu `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"`.
    - Lập tức `break` dừng phiên follow hiện tại để tránh spam.
    - Ở các phiên tiếp theo trong ngày của cùng máy: Chỉ riêng Nick Row X này bị **bỏ qua bước Follow (skip follow)** và chuyển sang **chỉ lướt nuôi Feed**.
    - Các Nick khác trên cùng máy đó (Row 1, Row 2, Row 4...) hoàn toàn không bị ảnh hưởng, vẫn chạy lướt Feed và Follow bình thường.
- **Phân biệt rạch ròi loại lỗi (CẤM gộp chung)**:
  - **Lỗi Nhả Follow thật (`FOLLOW_FAILED`)**: Đã bấm Follow nhưng khi vuốt reload trang thái nút bị nhả về "Follow"/"Follow lại" -> Chỉ áp dụng Cooldown cho lỗi này.
  - **Lỗi Điều hướng / Mở app / Tìm kiếm (`MANUAL_REVIEW`)**: Do mạng, app load chậm hoặc giao diện thay đổi -> Tuyệt đối KHÔNG gán cờ `follow_failed` để tránh chặn oan tài khoản.

## 2. Thống Kê Đặc Tính Nhả Follow
- **98.4% (123/125 ca)**: Nhả ngay lập tức từ mục tiêu đầu tiên (Followed = 0) do tài khoản bị TikTok Action Block / hạn chế tương tác từ đầu ngày.
- **1.6% (2/125 ca)**: Follow thành công được 1-2 người rồi mới bị nhả ở người tiếp theo do chạm hạn mức tương tác ngắn.

## 3. Khắc Phục Lỗi Parser JSON Gemini 3.7 Flash Trong AI Auto-Recovery
- **Gốc rễ sự cố**: Mô hình `ag/gemini-3.7-flash-high` qua 9Router phân tích ảnh rất thông minh và trả về JSON chuẩn nhưng được bọc trong Markdown Codeblock (` ```json ... ``` `).
- **Lỗi code cũ trong `vision_client.py`**: Regex `re.search` bị vướng tag markdown dẫn đến parse thất bại -> rơi vào `_FALLBACK_RESULT` (bị hardcode text rập khuôn *"Đã gửi phím Back để đóng màn hình"*).
- **Giải pháp triệt để**:
  - Strip và xóa bỏ triệt để các thẻ markdown codeblock (`^```(?:json)?\s*` và `\s*```$`) trước khi extract JSON.
  - Đảm bảo `ai_recovery/agent.py` luôn nhận được 100% kết quả phân tích AI thực tế từ Gemini (đúng chẩn đoán, đúng tọa độ tap/swipe và đúng hướng xử lý kỹ thuật).

## 4. Chu Trình Cron Nuôi Nick & Upload Hook Phiên Cuối Ca
- Chu kỳ 3 ca/ngày (06:00-10:00, 12:30-16:30, 19:00-23:00), mỗi ca 3 phiên (Session 1, 2, 3).
- **Upload Hook**: Tự động nhận diện phiên cuối cùng của ca (`session_index == 3`), kiểm tra workbook tương ứng (`Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`...), kiểm tra file video đã render sẵn (`D:\TIKTOK-videonuoinick\<folder>\<next>.mp4`) -> nếu đủ điều kiện sẽ tự động đăng bài, nếu chưa có video sẽ tự động safe-skip không làm gián đoạn hệ thống.
