# Creator Persona Binding & Representative Frames Extraction Invariant (2026-10-18)

## 1. Hiện trường & Sự cố thực tế (Incident M23 @huynhdiem0806)
- **Bối cảnh:** Chuẩn hoá toàn diện kênh `@huynhdiem0806` trên Máy 23 (Tik 3, slot 3).
- **Lỗi Lệch Pha Sổ Cái (Config Desync):** File Excel `Tik3.xlsx` dòng 23 từng có `Folder Video (Render) = 179` nhưng `Video Goc = 183`.
- **Sai Lầm Bốc Nhầm Ảnh Tĩnh (Stale/Adjacent Folder Trap):**
  - Coordinator thấy folder 183 có sẵn file `avatar.jpg` nên vội vàng cắt cúp và gửi preview.
  - Tuy nhiên, folder 183 chứa video của một cô gái khác hoàn toàn với creator nữ xuất hiện trong các video đời thường/ẩm thực của kho 179 (`D:\TIKTOK-videonuoinick\179`).
  - Hậu quả: Avatar mang phong cách và khuôn mặt của người khác, làm gãy hoàn toàn tính chân thực (persona consistency) của kênh. User lập tức phản ứng giận dữ: *"Ava kiểu gì v?"*.

---

## 2. Thẩm Định Kiến Trúc Từ Claude Sonnet 5.5 CLI
Claude Sonnet 5.5 đã chỉ rõ:
- **Nguyên nhân gốc:** Thiếu liên kết bắt buộc 1-1 giữa `creator_persona` và `asset_pool`. Việc chọn ảnh dựa trên số thứ tự thư mục lân cận (off-by-N: 183 vs 179) là lỗ hổng quy trình nghiêm trọng.
- **Nguyên tắc bất biến:** Avatar của kênh bắt buộc phải là khuôn mặt của chính creator xuất hiện trong các video đang phát trên kênh đó. Không có ngoại lệ.

---

## 3. Quy Trình Trích Xuất & Thẩm Định Avatar Chuẩn 4 Bước

### Bước 1: Khóa 1-1 Nguồn Video Hiện Hữu
- Xác định chính xác folder render thực tế của kênh: `D:\TIKTOK-videonuoinick\<folder>\`.
- CẬP NHẬT ngay `Tik*.xlsx`: Đưa `Video Goc` về đúng bằng `Folder Video` (ví dụ: `179` và `179`), cấm để lệch nguồn.

### Bước 2: Khai Thác Representative Frames
- Vào kho khung hình đại diện: `D:\TIKTOK-videonuoinick\<folder>\.avatar_work\representative_frames\`.
- Chọn khung hình cận cảnh có mặt creator chính:
  - Góc nhìn thẳng hoặc 3/4, nụ cười tươi tắn/tự nhiên.
  - Mặt chiếm $40\% - 60\%$ khung hình.
  - Ánh sáng rõ nét, không bị nhòe chuyển động (motion blur).
- Nếu kho representative frames chưa có ảnh đạt: dùng ffmpeg trích xuất trực tiếp từ các file MP4 đầu tiên (`1.mp4`, `2.mp4`...) tại các mốc giây sáng rõ.

### Bước 3: Cắt Cúp Chuẩn Lưới Ngũ Quan & Kiểm Chứng WinRT OCR
- Crop vuông tỉ lệ $1:1$ (tối thiểu $512 \times 512$ hoặc $640 \times 640$).
- Căn chỉnh tâm: Headroom $\ge 30\text{px}$, đỉnh tóc và cằm nằm trọn trong viền tròn profile TikTok, tuyệt đối cấm cắt cụt trán/cằm.
- **WinRT OCR Verification:** Chạy `python D:/Taadaa/tmp_winrt_ocr.py <image_path>`:
  - Xác nhận **100% không dính text, watermark, sticker, số tập hay phụ đề** đè lên ảnh.
  - Nếu OCR phát hiện bất kỳ chữ/số lạ nào $\rightarrow$ VETO NGAY LẬP TỨC, chọn frame khác.

### Bước 4: Preview Khung Tròn & Đăng Ký Receipt Trước Khi Gửi
- Tạo ảnh preview lồng viền tròn xanh để mắt nhìn thấy trước kết quả hiển thị trên app.
- Đăng ký visual receipt qua `guard_media_vision_gate.py --register-receipt`.
- Gửi thẻ `MEDIA:<path>` cho User kiểm tra bằng mắt thực tế.

---

## 4. Chốt Chặn Gate 6 Cơ Học (MISSING_MEDIA_EVIDENCE)
- Mọi thao tác thay đổi state trên thiết bị (Đổi tên, Đổi bio, Đổi avatar, Ghim video) đều tự động mở nghĩa vụ: `pending_media_obligation = True`.
- Cấm tuyệt đối báo cáo bằng văn bản thuần (text suông) mà không đính kèm thẻ `MEDIA:<path>` trên dòng riêng biệt.
- Hệ thống hook `transform_llm_output_check` trong `guard_media_vision_gate.py` tự động chặn đứng tin nhắn nếu có từ khóa hoàn tất (`đã đổi`, `thành công`, `hoàn tất`...) kèm thực thể UI (`tên`, `bio`, `avatar`, `profile`) mà thiếu thẻ `MEDIA:` hợp lệ.
