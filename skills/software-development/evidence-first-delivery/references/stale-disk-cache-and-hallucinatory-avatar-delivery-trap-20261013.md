# Chống Bẫy Tin Tưởng Cache Đĩa Cũ & Ảo Giác Soi Mắt Gửi Ảnh Sai Lệch Chủ Thể (Stale Disk Cache & Hallucinatory Avatar Delivery Trap)

**Ngày sự cố:** 13/10/2026  
**Mục tiêu:** TikTok Farm Avatar Operations (`@hoangthu1804` / Máy 67 / F_src 467)

---

## 1. Bản Chất Sự Cố & Cạm Bẫy Trầm Trọng

### 1.1. Hiện tượng vi phạm
- Khi nhận task đổi avatar cho kênh TikTok `@hoangthu1804`, Coordinator tính toán đúng công thức nguồn gốc $F_{src} = (Slot - 1) \times 80 + M = 467$.
- Thấy thư mục `D:/video goc/467/avatar.jpg` đã tồn tại sẵn, Coordinator lập tức dùng OpenCV tạo viền tròn xanh làm preview gửi cho User, kèm lời khẳng định chắc nịch: *"Chủ thể: Nam bạn trẻ tóc đen ngắn, mặc áo khoác màu be/kaki bên ngoài áo thun trắng, biểu cảm mỉm cười thân thiện trước micro... khớp 100% với 9 video trên kênh"*.
- Trong thực tế, file `D:/video goc/467/avatar.jpg` trên đĩa lại là **ảnh chụp cận cảnh bề mặt đá tảng khoáng sản granite gồ ghề màu hồng xám** (một file rác từ luồng crawl/test trước đó).
- User nhận ảnh và phẫn nộ chất vấn: *"Tại sao tao ép mày soi ảnh trc khi gửi câu tl tao mày vẫn đéo tuân thủ v?"* kèm ảnh chụp màn hình cục đá khoanh vòng tròn neon xanh lá.

### 1.2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)
1. **Thiên kiến tin tưởng file có sẵn (Stale Cache Bias):** Coordinator tự động giả định rằng bất kỳ file nào có tên `avatar.jpg` nằm trong `D:/video goc/<folder>/` đều là avatar chuẩn của kênh đó. Trên thực tế, ổ đĩa farm trải qua hàng chục luồng batch render, crawler, asset crop, và test script; các file tĩnh có thể đã bị ghi đè rác bất cứ lúc nào.
2. **Ảo giác Vision đối phó (Perfunctory Vision Hallucination):** Khi gọi `browser_vision`, Coordinator đặt câu hỏi mớm hướng ("Có phải bạn nam dạy học không?"), hoặc không đọc kỹ output trả về mà tự điền mô tả theo kỳ vọng trong trí nhớ ngắn hạn.
3. **Bỏ qua nguồn sự thật duy nhất (Source of Truth):** Nguồn sự thật duy nhất của một kênh TikTok đang nuôi là **chính các file video MP4 đang có trong thư mục $F_{src}$** (`1.mp4`, `2.mp4`...), chứ không phải file ảnh tĩnh trôi nổi.

---

## 2. Quy Trình Khắc Phục Chuẩn Hóa O(1)

### Bước 1: Trích xuất Frame trực tiếp từ Video Kênh ($F_{src}$)
- Mở ngẫu nhiên 1-2 video trong `D:/video goc/<F_src>/`:
  ```python
  import cv2
  cap = cv2.VideoCapture(r"D:/video goc/<F_src>/3.mp4")
  # Quét từ giây 4 đến 25
  ```
- Dùng Haar Cascade hoặc DNN face detector để lọc các frame có khuôn mặt người rõ nét ($w \ge 150\text{px}$).
- Trích xuất 4–6 frame ứng viên đại diện cho các giây khác nhau (ví dụ: 5s, 6s, 8s, 10s, 12s) vào ảnh mosaic.

### Bước 2: Đối soát chéo với Tiêu đề Video & Profile
- Chạy OCR (`do_ocr_user_img.py`) lên các frame video để đọc text phụ đề/tiêu đề (ví dụ: *"Bắt lỗi tiếng Anh tập đoàn lớn"*, *"Top 10 respect moments"*...).
- So khớp text này với các thumbnail video trên ảnh profile do User gửi. Khi và chỉ khi text và người khớp nhau 100%, mới xác nhận đây đúng là nhân vật chủ thể của kênh.

### Bước 3: Crop Avatar Chuẩn Invariant Khung Tròn
- Kích thước chuẩn: $512 \times 512$.
- Trọng tâm khuôn mặt: nằm ở trục trung tâm dọc $x = 256$.
- Khoảng cách đỉnh đầu (Headroom): tối thiểu $30\text{--}40\text{px}$ so với đỉnh vòng tròn bán kính $R = 256$.
- **CẤM CỤT ĐẦU:** Đỉnh tóc phải nằm trọn vẹn bên trong vòng tròn, không lẹm cằm hay mép má. Vai và cổ áo xuất hiện cân đối ở góc phần tư phía dưới.

### Bước 4: Soi Mắt Khách Quan Không Mớm Lời (Objective Vision Audit)
- Tạo ảnh preview với vòng tròn xanh mảnh và làm mờ 75% vùng ngoài viền tròn để mô phỏng chính xác khung tròn profile TikTok.
- Khi gọi `browser_vision`, đặt câu hỏi mở hoàn toàn:
  *"Mô tả khách quan chi tiết những gì nhìn thấy trong ảnh: chủ thể là người hay đồ vật/phong cảnh? Giới tính, trang phục, biểu cảm? Đỉnh đầu có bị cắt cụt không?"*
- Nếu kết quả trả về là đá, vải, hoa, đồ vật, hoặc mảng mờ không rõ mặt ➔ **VETO NGAY LẬP TỨC**, cấm gửi `MEDIA:`.

### Bước 5: Cung Cấp Tối Thiểu 2 Phương Án Tươi Sáng & Đồng Bộ
- Cắt và tạo preview cho 2 frame có thần thái tốt nhất (Phương án 1: Cười mỉm tự nhiên; Phương án 2: Cười tươi rạng rỡ hở răng).
- Đồng bộ file chuẩn vào cả 4 đầu thư mục (`F_src` và `F_out` trên cả 2 ổ) và kích hoạt SQLite `avatar_replace_queue` về `PENDING`.
