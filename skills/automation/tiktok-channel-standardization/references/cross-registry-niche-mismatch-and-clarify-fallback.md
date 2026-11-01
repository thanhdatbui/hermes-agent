# Kỷ Luật Đối Soát Lệch Niche Chéo Đa Tầng & Cơ Chế Dự Phòng Khi Clarify Bị Chặn

## 1. Bẫy Lệch Niche Chéo Giữa Bảng Tính Excel Và Kho Video Thật (Cross-Registry Mismatch)
- **Thực trạng phát hiện:**
  - Một số tài khoản sau các đợt reg nick hàng loạt hoặc gán nhầm dòng bị sai lệch Niche trong file Excel `Tik<N>.xlsx`.
  - Ví dụ điển hình: Kênh `@vyvy14190` (Máy 274, `Tik5.xlsx` Row 75) bị ghi nhầm `Keyword Video: Anime` và gán `Hashtag Pool` của Anime, trong khi video thực tế đã đăng (884 views) và 52 video trong kho gốc `F_src 394` / render `F_vid 589` là nội dung **Thú Cưng / Cún Cưng Múa Bụng**.
- **Kỷ luật sửa chữa 5-in-1 toàn diện:**
  - Khi xuất bản Proposal Canvas, Coordinator BẮT BUỘC phải đọc trực tiếp nội dung video thực tế (qua sampling frame và kiểm tra màu/chủ thể) thay vì chỉ tin vào text trong Excel.
  - Hạng mục thứ 5 trong Proposal Canvas BẮT BUỘC bao gồm việc đồng bộ sửa lại:
    * `Keyword Video`: Chuyển về đúng ngách thực tế (ví dụ: `Thú Cưng / Chó Cưng`).
    * `Hashtag Pool`: Thay thế toàn bộ hashtag lệch bằng bộ hashtag chuẩn của ngách.
    * Khóa thư mục: Cắm marker `.manual_avatar_locked` & `.manual_hashtag_locked` vào cả hai thư mục `F_src` và `F_vid`.

## 2. Kỷ Luật Dự Phòng Khi Lệnh `clarify` Bị Chặn (Handoff Lock Fallback)
- **Tình huống kích hoạt:**
  - Khi Coordinator tạo xong bảng Proposal Canvas 5-in-1, đăng ký Vision Receipt và muốn lấy ý kiến User chọn phương án (PA 1 - PA 4), nếu gọi công cụ `clarify` mà bị hệ thống Guard từ chối (ví dụ: do có file khóa `handoff_lock_active.json` còn tồn đọng từ các phiên remediation trước).
- **Nguyên tắc hành động chống bại liệt:**
  - CẤM TUYỆT ĐỐI dừng lại, bỏ dở task hoặc than phiền về lỗi công cụ.
  - Coordinator chuyển ngay sang cơ chế trình bày trực tiếp trong văn bản chat:
    1. Tóm tắt toạ độ Farm O(1) (Máy, Slot, Serial, Kho video, Chỉ số thực tế).
    2. Chẩn đoán rõ ràng các điểm lệch (Creator Mismatch, Niche Mismatch).
    3. Đăng ký Vision Receipt (`create_vision_receipt`) và kiểm chứng mắt thật qua `browser_vision`.
    4. Trình bày chi tiết 4 phương án đề xuất kèm thẻ `MEDIA:<path_to_canvas>`.
    5. Đặt câu hỏi trực tiếp ở cuối tin nhắn để User trả lời bằng text thông thường.
