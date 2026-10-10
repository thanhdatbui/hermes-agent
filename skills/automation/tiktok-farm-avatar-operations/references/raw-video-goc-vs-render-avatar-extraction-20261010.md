# Raw Video Gốc vs Render Video Avatar Extraction Discipline (2026-10-10)

## Context & Operator Correction
Trong phiên xử lý nick `@trn.m.m620` (Máy 26 Tik 1 Kibe, Folder Video 201), khi Operator ra lệnh: *"Quét lại tạo ava coi"*, Coordinator ban đầu đã quét và trích xuất các frame từ `D:\TIKTOK-videonuoinick\201`.
Hậu quả:
- Toàn bộ các frame trích xuất từ folder render đều bị Vision đánh FAIL (điểm 3.5 - 5.8/10) do:
  1. Pipeline render can thiệp hiệu ứng: chèn dark vignette nặng ở đỉnh/đáy màn hình (làm đỉnh đầu/tóc bị tối sầm, mất chi tiết).
  2. Bị can thiệp zoom/crop, đổi tỷ lệ khung hình (ép từ 576x1024 lên 1080x1920) làm rỗ pixel và bệt da.
  3. Bị chèn filter màu/LUT khiến màu da không tự nhiên.
- Operator chấn chỉnh gay gắt và ra lệnh dứt khoát:
  **"Lấy từ video gốc ấy đừng lấy từ render"**

---

## Root Cause Analysis: Bản chất Kho Render vs Kho Gốc

| Tiêu chí | Kho Video Gốc Raw (`D:\video goc\<video_goc>`) | Kho Video Render (`D:\TIKTOK-videonuoinick\<folder_video>`) |
| :--- | :--- | :--- |
| **Bản chất** | File gốc nguyên bản tải trực tiếp từ TikTok/Douyin | File thành phẩm đã xử lý re-up/chống quét bản quyền |
| **Độ phân giải** | Gốc (ví dụ 576x1024, 540x960, 576x828) | Ép tỷ lệ 1080x1920, bị scale và crop khung hình |
| **Hiệu ứng đồ họa** | **Không có hiệu ứng nhân tạo** (sạch 100%) | Đã chèn vignette tối, chỉnh sáng, bệt mịn da, lật gương |
| **Độ nét micro** | Đồng tử, lông mi, chân tóc sắc nét tự nhiên | Mờ viền, rỗ hạt nén video hoặc mất chi tiết da |
| **Mục đích dùng** | **CHUYÊN DÙNG ĐỂ TRÍCH XUẤT AVATAR ĐỘC BẢN** | Dành riêng cho bot đăng bài lên TikTok thiết bị |

---

## Quy trình Chuẩn hóa 5 Bước Trích xuất Avatar từ Video Gốc

### Bước 1: Xác định thư mục Video Gốc thực tế
- Tra cứu dòng tài khoản trong `Tik<N>.xlsx`:
  - `Folder Video` (ví dụ `201`)
  - `video gốc` (ví dụ `26`, công thức `(Tik-1)*80 + Máy`)
- Kiểm tra trực tiếp thư mục `D:\video goc\<video_goc>`:
  - Xác nhận danh sách file `.mp4` gốc có thời lượng khớp với nội dung kênh.
  - CẤM TUYỆT ĐỐI trích xuất từ `D:\TIKTOK-videonuoinick` khi đã biết số thư mục video gốc.

### Bước 2: Quét frame thô trên Video Gốc (Raw Frames)
- Quét nhanh các frame từ các video raw trong `D:\video goc\<video_goc>` bằng OpenCV:
  - Chọn các video có chân dung creator (ví dụ `38.mp4`, `3.mp4`, `27.mp4`).
  - Lấy frame tại các timestamp ổn định (tránh 0.5s đầu bị chớp đen/chuyển cảnh).
  - Kiểm tra độ sắc nét Laplacian variance (`sharpness >= 50`).

### Bước 3: Thẩm định Vision & Cắt cúp Vuông 512x512
- Dùng Vision API (qua 9Router model `ag/gemini-3.7-flash-high`) đánh giá frame raw:
  - Xác nhận trực diện, mắt nhìn thẳng ống kính, nụ cười tự nhiên.
  - Sạch 100% chữ phụ đề, logo CapCut, tay/đạo cụ che mặt.
- Cắt cúp vuông tỷ lệ 1:1 sao cho:
  - Đỉnh tóc có 8–12% khoảng thở tự nhiên (headroom).
  - Mắt nằm ở 1/3 trên của khung hình.
  - Cằm và cổ áo cân đối bên trong vòng tròn avatar.
  - Điểm thẩm định Vision đạt $\ge 8.5/10$ (thực tế case video 38 đạt **9.1/10**).

### Bước 4: Đồng bộ File Ảnh Nguyên Tử 3 Đầu Kho
Khi `video_goc` khác số với `folder_video` (ví dụ gốc `26` vs render `201`), bắt buộc ghi đè nguyên tử qua `.tmp.jpg` $\to$ `.replace()` vào cả 3 thư mục:
1. `D:\video goc\<video_goc>\avatar.jpg`
2. `D:\video goc\<folder_video>\avatar.jpg`
3. `D:\TIKTOK-videonuoinick\<folder_video>\avatar.jpg`

### Bước 5: Cập nhật Sổ cái và Hàng đợi SQLite
1. **Excel `Tik<N>.xlsx`**:
   - Cột `video gốc`: gán đúng số thư mục gốc (ví dụ `26`).
   - Cột `Avatar`: đặt `PENDING`.
2. **SQLite `tiktok_tracker.db` (`avatar_replace_queue`)**:
   - `UPDATE avatar_replace_queue SET folder_video='<folder_video>', video_goc='<video_goc>', status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='<username>';`
   - Đảm bảo watchdog ca tối tự động upload ảnh mới lên thiết bị thật.
