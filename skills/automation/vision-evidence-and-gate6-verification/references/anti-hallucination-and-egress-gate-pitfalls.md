# Mechanical Enforcement: Anti-Hallucination & Egress Gate Pitfalls

## 1. Bản Chất Vấn Đề (Hallucination Loop Dù Đã Có Vision Tool)
Khi Agent sử dụng `browser_vision` mở ảnh ra kiểm tra, model multimodal có thể "thấy" pixel nhưng model sinh văn bản (LLM) lại **bịa đặt câu chuyện hoàn toàn khác** trong tin nhắn chat để làm hài lòng prompt nghiệp vụ (ví dụ: thấy ảnh người đàn ông/người phụ nữ/bàn tay dầu mỡ nhưng text vẫn quả quyết "đây là cún cưng múa bụng, cún nghiêng đầu").

## 2. Các Lỗ Hổng Cơ Học Khiến Gate Bị Vô Hiệu Hóa
1. **Lỗ hổng Regex Dirty Check tự bắn vào chân:**
   * Trong `guard_media_vision_gate.py`: Kiểm tra regex `r"(?<!\w)(?:\d{1,3}(?:[.,]\d{3})+|\d{3,})(?!\w)"` để bắt số view video (như `10.5K`, `1200`) trên avatar.
   * Nhưng Proposal Canvas tổng hợp luôn in **số máy** (ví dụ: `274`). Regex phát hiện 3 chữ số này ➔ Gate đánh nhãn `DIRTY_AVATAR_EVIDENCE` và tự động âm thầm nuốt (strip) thẻ `MEDIA:`!
   * **Khắc phục:** Tách biệt ảnh crop avatar thuần túy (`is_pure_crop`) với proposal canvas tổng hợp (`proposal`, `canvas`). Chỉ kiểm tra số view trên crop thuần túy.

2. **Lệch SHA256 Hash Giữa Các Bản Build Canvas:**
   * Khi code generator render lại canvas mới, hash của file trên đĩa thay đổi (`sha256_new`).
   * Nếu receipt được tạo trước khi file ghi xong hoặc trỏ vào hash cũ, Gate thấy `receipt.sha256 != file.sha256` ➔ Đánh rớt `NO_RECEIPT` ➔ Strip `MEDIA:`.
   * **Khắc phục:** Luôn tạo receipt sau khi file ảnh đã được ghi hoàn tất xuống đĩa và tính hash trên file thực tế.

3. **Cấm Dùng WinRT OCR Để Lách Cửa Vision:**
   * WinRT OCR chỉ đọc được text, mù hoàn toàn về nội dung hình học và chủ thể trong các ô tròn.
   * Mọi ảnh visual (`proposal`, `canvas`, `cand`, `preview`, `avatar`) BẮT BUỘC `tool_called` phải nằm trong allowlist `('browser_vision', 'ag_cli_vision')`. Tuyệt đối cấm cấp receipt từ `winrt_ocr`.

4. **Tránh Deadlock Codec Video Bằng Process Isolation:**
   * Tuyệt đối không gọi `cv2.VideoCapture` trực tiếp trong luồng foreground của terminal (dễ bị deadlock C++ Media Foundation trên Windows gây treo 60 phút).
   * Bắt buộc bọc qua `safe_extract_video_frame` chạy trong subprocess riêng với hard-timeout 10s và `taskkill /F /T /PID` để dọn sạch cây tiến trình con.
