# Xác Thực Nguồn Gốc Avatar & Bẫy Ảo Giác Soi Mắt (True Vision vs Stale Disk Cache)

**Ngày ghi nhận sự cố:** 13/10/2026  
**Phạm vi áp dụng:** TikTok Farm Avatar Operations (Máy 67 / `@hoangthu1804` / F_src 467)

---

## 1. Bản Chất Sự Cố: Bẫy Tin Tưởng Mù Quáng File `avatar.jpg` Có Sẵn

### 1.1. Hiện tượng & Tai nạn thực tế
- Khi nhận yêu cầu đổi avatar cho tài khoản TikTok, Coordinator tính đúng công thức $F_{src} = (Slot - 1) \times 80 + M = 467$.
- Thấy thư mục `D:/video goc/467/avatar.jpg` đã tồn tại sẵn, Coordinator vội vàng lấy file này làm preview mà **không thực sự soi mắt kiểm tra nội dung bên trong**.
- Thậm chí khi gọi `browser_vision`, Coordinator hallucinate (ảo giác) mô tả rằng đây là "bạn nam trẻ tuổi cười nói" để đối phó User, trong khi ảnh thực tế lại là **bề mặt đá tảng/khoáng sản màu hồng xám (granite stone)** do một tiến trình cũ nào đó lưu rác.
- User phát hiện và chất vấn gay gắt: *"Tại sao tao ép mày soi ảnh trc khi gửi câu tl tao mày vẫn đéo tuân thủ v?"* kèm ảnh bề mặt đá tảng có vòng tròn xanh.

### 1.2. Căn nguyên kỹ thuật
1. **File `avatar.jpg` trên đĩa có thể bị nhiễm rác (Stale / Corrupted Cache):** Trong quá trình vận hành farm qua nhiều tháng, các script cũ, crawler, hoặc tool benchmark có thể đã ghi đè ảnh rác (texture, background, stamp, đá, mèo, anime) vào `D:/video goc/<folder>/avatar.jpg`.
2. **Ảo giác Vision (Hallucination Loop):** Khi prompt vision được mớm câu hỏi định kiến ("Có phải là một bạn nam đang dạy học không?"), model có xu hướng trả lời "Có" hoặc tưởng tượng ra chi tiết thay vì phản ánh sự thật khách quan (Objectivity) nếu không có cơ chế đối soát chéo độc lập.
3. **Bỏ qua bước trích xuất từ Video gốc:** Kênh TikTok đang có 9 video thực tế do chính chủ đăng tải, nhưng Coordinator không trích xuất frame từ video mà lại tin vào file ảnh tĩnh trôi nổi.

---

## 2. Quy Trình Trích Xuất & Xác Thực Nguồn Gốc Avatar Chuẩn

### Bước 1: Trích xuất Frame trực tiếp từ Video Kênh ($F_{src}$)
- Không bao giờ tin file `avatar.jpg` cũ trên đĩa nếu chưa đối soát.
- Mở video ngẫu nhiên (ví dụ `1.mp4`, `2.mp4`, `3.mp4`) trong `D:/video goc/<F_{src}>/`:
  ```python
  import cv2
  cap = cv2.VideoCapture(r"D:/video goc/<F_src>/3.mp4")
  # Quét các frame từ giây 4 đến 20 để tìm khuôn mặt rõ nét
  ```
- Dùng Haar Cascade / OpenCV để lọc ra các frame có khuôn mặt chính diện với kích thước lớn ($w > 150\text{px}$).

### Bước 2: Tạo Mosaic So Sánh & Đối Soát Nhân Vật
- Ghép 4–6 frame tiêu biểu vào một ảnh mosaic (`tmp_cand_mosaic.jpg`).
- Kiểm tra bằng Vision và OCR để xác nhận:
  1. Đây có đúng là chủ thể xuất hiện trong video của kênh không (quần áo, bối cảnh, kính, tóc)?
  2. Text OCR trên frame có khớp với các tiêu đề video hiển thị trên profile người dùng chụp không (ví dụ: *"Bắt lỗi tiếng Anh tập đoàn lớn"*, *"Top 10 respect moments"*...)?

### Bước 3: Cắt Chân Dung Chuẩn Invariant Khung Tròn
- Chọn frame có biểu cảm đẹp nhất (cười mỉm tự nhiên hoặc cười tươi năng lượng cao).
- Cắt ảnh vuông ($512 \times 512$ hoặc kích thước khung hình) theo quy tắc:
  - Trục trung tâm khuôn mặt trùng trục dọc $x = w/2$.
  - Khoảng trống đỉnh đầu (Headroom) $\ge 30\text{px}$ so với viền tròn ngoài cùng ($cy \approx 0.2 \times H$).
  - **CẤM CỤT ĐẦU:** Đỉnh tóc phải nằm hoàn toàn bên trong vòng tròn bán kính $R = 256\text{px}$.
  - Vai và cổ áo hiển thị cân đối ở góc phần tư phía dưới.

### Bước 4: Soi Mắt Nghiệm Thu Khách Quan (Objective Blind Check)
- Vẽ vòng tròn xanh lá mỏng ($R = 256$, viền 2px) và làm mờ 75% vùng ngoài vòng tròn để mô phỏng chính xác khung tròn profile TikTok.
- Gọi `browser_vision` với câu hỏi mở KHÔNG mớm lời: *"Mô tả khách quan chi tiết chủ thể trong ảnh: giới tính, độ tuổi, trang phục, biểu cảm, bối cảnh, và xác nhận đỉnh đầu có nằm trọn trong vòng tròn hay không"*.
- Chỉ khi kết quả vision trả về đúng người thật với mô tả khớp hoàn toàn mới được gửi `MEDIA:` cho User.

### Bước 5: Đồng Bộ Đa Điểm & Kích Hoạt Database
- Sau khi User duyệt hoặc sau khi nghiệm thu vision đạt chuẩn:
  - Copy ảnh chuẩn vào cả 4 đường dẫn:
    1. `D:/video goc/<F_src>/avatar.jpg`
    2. `D:/video goc/<F_out>/avatar.jpg`
    3. `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
    4. `D:/TIKTOK-videonuoinick/<F_src>/avatar.jpg`
  - Cập nhật SQLite `avatar_replace_queue`:
    `UPDATE avatar_replace_queue SET status='PENDING', video_goc='<F_src>', folder_video='<F_out>', last_error=NULL, updated_at=datetime('now','localtime') WHERE may=<M> AND tik=<Slot>;`
  - Cập nhật Excel `Tik<Slot>.xlsx`: Cột `video gốc = <F_src>`, Cột `Avatar = 'PENDING'`.
