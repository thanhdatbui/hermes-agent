# News Video Rejection, Niche Swap Invariant, and Anti-Browser-Vision Discipline (2026-11-03)

## 1. Phát hiện Nguồn Tin tức / Phóng sự (News Content Trap)
- **Dấu hiệu nhận biết:** Khi trích xuất avatar chân dung từ kho video gốc bằng Haar Cascade / Face Detection, nếu 100% khuôn mặt trích xuất được đều là **nhân vật đang trả lời phỏng vấn thời sự, bản tin xã hội, phóng sự điều tra**, kèm micro, logo đài truyền hình hoặc góc máy lén/quay nhanh.
- **Kỷ luật tối cao (Ground Truth Policy):**
  - **CẤM TUYỆT ĐỐI** dùng video tin tức / thời sự / phóng sự để nuôi acc TikTok. Kênh tin tức bị bóp reach (shadowban), dễ dính gậy bản quyền và không chuyển đổi được.
  - Khi phát hiện kho video gốc là tin tức (dù trong Excel ghi "Ô tô" hay "Câu chuyện"): **DỪNG NGAY** việc cố crop ảnh mặt nhân vật tin tức làm avatar.
  - Phải lập tức kích hoạt quy trình **ĐỔI NGUỒN TRIỆT ĐỂ (Full Source Swap)**:
    1. Dọn sạch 100% kho render cũ (`D:/TIKTOK-videonuoinick/<F>`) và kho gốc cũ (`D:/video goc/<F>`).
    2. Chọn ngách hot sạch chữ dựa trên dữ liệu cắn đề xuất thực tế của Farm (Ưu tiên: **Ẩm thực / Bếp Việt**, **Thú cưng / Chó mèo**, **Hài hước / Tiểu phẩm**).
    3. Bảo lưu nguyên vẹn cursor `Video Đã Đăng` (ví dụ đã đăng 10 video thì render tiếp nối từ `11.mp4`).

## 2. Kỷ luật Native Multimodal Vision vs Chống Làm Màu Bằng Browser
- **Sự cố:** Agent mở file ảnh local bằng `browser_navigate(file:///...)` và gọi `browser_vision` để "soi mắt", sau đó bịa đặt mô tả chi tiết ("bạn nữ nhân viên công sở tóc đen mặc áo sơ mi trắng...") khi model thực chất chưa hề nhận diện được pixel thật.
- **Nguyên nhân:** Bị chi phối bởi câu lệnh cũ trong `SOUL.md` ép phải gọi `browser_vision` trước khi gửi `MEDIA:`, trong khi model đang chạy là Native Multimodal (`ag-gemini-pool-3`).
- **Quy chuẩn chuẩn hóa:**
  1. **Không mở browser đối phó:** CẤM dùng `browser_navigate` / `browser_vision` để mở file ảnh cục bộ trên máy tính.
  2. **Native Vision:** Với model Gemini, ảnh do user gửi vào chat được Gateway nạp trực tiếp dạng pixel base64 vào prompt của model.
  3. **Thẩm định ảnh cục bộ trước khi gửi:** Kiểm tra text/UI bằng **WinRT OCR** thật hoặc các thuật toán đo độ nét cơ học (Laplacian variance, Canny edge detection), TUYỆT ĐỐI CẤM bịa đặt mô tả hình ảnh bằng văn bản khi chưa nhìn thấy pixel.
