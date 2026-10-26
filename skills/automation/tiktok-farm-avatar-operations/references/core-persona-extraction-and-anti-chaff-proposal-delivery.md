# Core Persona Extraction & Anti-Chaff Proposal Delivery

## 1. Trích Xuất Đúng Chủ Thể (Core Persona vs B-Roll/Workspace)

### Bẫy kỹ thuật thường gặp
Khi lấy mẫu frame tự động từ kho video gốc (`D:/video goc/<id>`):
- Nếu quét ngẫu nhiên các video b-roll hoặc phụ cận (ví dụ video 15, 20, 25...), script phát hiện khuôn mặt thường bắt nhầm:
  1. Người qua đường, diễn viên phụ, hoặc bạn bè trong các cảnh ngoại cảnh.
  2. Góc bàn làm việc công nghệ tối giản (không lộ mặt người).
  3. Cảnh minh họa màn hình code.
- Hậu quả: Đề xuất sai nhân vật cho kênh (ví dụ kênh lập trình viên nam đeo kính nhưng đề xuất góc làm việc không mặt hoặc nam không kính).

### Quy tắc bất biến khi trích xuất Persona
1. **Lấy mẫu từ Video Cốt Lõi (Core Speaking/Milestone Videos):**
   - Ưu tiên số 1: Video có lượt xem cao nhất đã ghim trên profile hoặc các video có người ngồi nói trực diện vào camera (nói trước micro, chia sẻ kiến thức).
   - Ưu tiên số 2: Video sự kiện quan trọng của chủ kênh (tốt nghiệp, phỏng vấn, giới thiệu kênh).
2. **Khớp Nhân Vật Tuyệt Đối:**
   - Kiểm tra đặc điểm nhận dạng cốt lõi: Giới tính, kính mắt, trang phục, góc mặt chính diện.
   - Khi phát hiện nhiều mặt trong cùng frame, chọn bounding box có diện tích lớn nhất và nằm ở trung tâm khung hình.

---

## 2. Kỷ Luật Trình Phương Án Ảnh (Anti-Chaff Delivery)

### Triệu chứng vi phạm
Khi User ra lệnh: `"Còn lại xử lý đi"`, `"Chuẩn hoá kênh này"`:
- Agent không gửi ảnh mà in ra một đoạn văn dài tóm tắt kế hoạch, giải thích hiện trường ("lải nhải đéo làm").
- User phản ứng gay gắt: *"Là sao nữa ava chuẩn bị lại đâu? Cứ lải nhải..."*

### Quy tắc giao tiếp & Bằng chứng trực quan
1. **Visual Evidence First:**
   - Dòng đầu tiên của tin nhắn BẮT BUỘC là thẻ `MEDIA:<path_anh_canvas_proposals>`.
   - Bảng ảnh canvas phải ghép sẵn các phương án (PA 1A, 1B, 2A, 2B...), crop tròn $512 \times 512$ giả lập hiển thị avatar TikTok thực tế.
2. **Soi Mắt Qua Vision Trước Khi Bắn Thẻ:**
   - Bắt buộc kiểm tra bằng WinRT OCR hoặc Vision Gate để đảm bảo:
     - Đúng chủ thể theo đúng mô tả của kênh.
     - Không bị méo, lẹm viền, hay chữ che khuất mặt.
3. **Format Ngắn Gọn Dưới 15 Dòng:**
   - Nêu ngắn gọn 2–4 lựa chọn để User chốt nhanh (ví dụ: `K1: 1A, K2: 2A`). Tuyệt đối không viết sớ giải thích quy trình hay liệt kê tiến trình nền.
