# Quy Tắc Trích Xuất Avatar Khớp Chủ Thể & Bảng Phương Án Trực Quan (Proposal Canvas)

## 1. Bẫy Lệch Chủ Thể Khi Trích Xuất Avatar (Creator-Bound Invariant)
- **Hiện tượng lỗi:** Khi chuẩn bị avatar cho kênh chuyên gia/creator (ví dụ nam đeo kính chia sẻ lập trình), agent quét ngẫu nhiên các video số cao trong kho (`vid_15`, `vid_25`...) dẫn đến crop nhầm cảnh b-roll, góc bàn máy tính không người, hoặc người khác trong clip minh họa.
- **Quy tắc bắt buộc:**
  1. **Đối soát Profile Grid:** Trước khi trích frame, soi mắt lưới video trên Profile TikTok để xác định nhân diện chính của kênh (giới tính, kính mắt, trang phục, vai trò diễn giả/người nói).
  2. **Nhắm trúng Video Cốt Lõi:** Ưu tiên trích xuất từ video ghim (Pin Top), video có giọng nói/nói trước micro, hoặc các video đầu tiên (`1.mp4`, `2.mp4`, `4.mp4`...).
  3. **Công cụ trích xuất nhanh O(1):** Dùng `python D:/Taadaa/tools/video_contact_sheet.py <video> --output <out>` để tạo nhanh Contact Sheet 3x3 kiểm tra visual toàn bộ video trong 1 giây trước khi crop.

## 2. Kỷ Luật Trình Bày Phương Án: Action-First (Tuyệt Đối Không Gửi Lời Hứa Suông)
- **Tâm lý User:** Khi user giục "ava chuẩn bị lại đâu", user muốn THẤY ẢNH NGAY LẬP TỨC để chọn (A/B/C), không muốn đọc văn xuôi phân tích hay giải thích quy trình.
- **Tiêu chuẩn Canvas Phương Án:**
  - Luôn ghép các phương án thành 1 ảnh Canvas tổng hợp (`create_proposal_canvas.py` hoặc tương đương).
  - Mỗi phương án gồm ảnh vuông $512 \times 512$ có bọc viền tròn mô phỏng giao diện hiển thị thật của TikTok.
  - Đăng ký Vision Receipt qua `guard_media_vision_gate.py` để tin nhắn không bị gate nuốt chửng.
  - Gửi kèm thẻ `MEDIA:<path>` ngay dòng đầu tiên. Tuyệt đối không bao giờ gửi tin nhắn miêu tả phương án mà thiếu thẻ `MEDIA:`.

## 3. Tôn Trọng Tên Teencode / Phong Cách Đặt Tên Của User
- Không tự ý "chuẩn hoá" bẻ tên hiển thị của tài khoản nếu phong cách viết hoa/teencode (ví dụ `Ngọc TRinh`) là chủ đích tự nhiên của người dùng TikTok. Chỉ can thiệp tên khi tên bị rác hệ thống (dính số ngẫu nhiên lúc reg, ký tự vô nghĩa).
