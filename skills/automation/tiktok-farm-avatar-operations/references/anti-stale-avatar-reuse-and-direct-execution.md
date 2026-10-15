# Kỷ Luật Trích Xuất Avatar Mới & Chống Dùng Lại Avatar Cũ (Anti-Stale Avatar Reuse)

## 1. Tín Hiệu & Bối Cảnh Lỗi (Root Cause & User Frustration)
Khi User gửi ảnh một kênh kèm chỉ thị:
- *"Chuẩn hoá kênh này"*
- *"Đổi ava nick này"*

**Bẫy ngộ nhận nguy hiểm:**
- Coordinator thấy trong thư mục `D:\TIKTOK-videonuoinick\<F_out>\avatar.jpg` hoặc `D:\video goc\<F_src>\avatar.jpg` đã có sẵn file `avatar.jpg`.
- Coordinator vội vàng gọi runner đẩy file `avatar.jpg` đó lên TikTok app.
- **Hậu quả:** File `avatar.jpg` đó chính là avatar cũ đang hiển thị trên kênh (hoặc file từ lần tạo trước bị lỗi/user không ưng). User thấy avatar trên kênh không hề thay đổi hoặc bị nạp lại đúng ảnh cũ và tức giận phản ứng: *"dụd mẹ t ns đổi ava mày đưa y cái ava cũ ăn lồn à"*.

---

## 2. Invariant Cốt Lõi: Đổi Avatar Là BẮT BUỘC Phải Có Avatar MỚI
1. **CẤM TUYỆT ĐỐI đẩy `avatar.jpg` có sẵn** khi chưa so khớp trực quan với avatar hiện tại của kênh:
   - Nếu kênh đã có avatar (không phải ảnh mặc định màu xám), BẮT BUỘC phải trích xuất ứng viên avatar MỚI từ kho video gốc `D:\video goc\<F_src>\`.
   - Cấm suy diễn `avatar.jpg` có sẵn là ảnh mới.

2. **Quy Trình Tạo Avatar Mới Từ Video Gốc (`F_src`):**
   - Đọc các frame tiêu biểu trong `D:\video goc\<F_src>\.avatar_work\representative_frames\` hoặc trích xuất từ các video `*.mp4` bằng OpenCV/HaarCascade.
   - Lọc các frame có khuôn mặt chính diện, rõ nét (đo `Laplacian.var() > 200`), biểu cảm tươi cười/phù hợp niche (như ngách Cười, Gia đình, Thú cưng...).
   - Đảm bảo tỷ lệ Headroom: Khoảng cách từ đỉnh đầu đến mép trên ảnh chiếm 25-35% chiều cao khuôn mặt để khi TikTok cắt bo tròn (Circle Crop) không bị cụt tóc, bay đầu.
   - Resize chuẩn `512x512` Lanczos.
   - **Ghi đè đồng bộ 3 đầu kho:**
     1. `D:\video goc\<F_src>\avatar.jpg`
     2. `D:\video goc\<F_out>\avatar.jpg`
     3. `D:\TIKTOK-videonuoinick\<F_out>\avatar.jpg`

3. **Kỷ Luật Khởi Động Runner Nạp Avatar (Chống Hỏi Suông / Chống Chờ Nhắc):**
   - Khi nhận lệnh *"Chuẩn hoá kênh"* / *"Đổi ava"*: User muốn Coordinator TỰ ĐỘNG THỰC THI DỨT ĐIỂM, cấm hỏi lại *"anh có muốn đổi không"* hay ngồi im chờ nhắc nhở.
   - Đặt `Avatar = PENDING` trong file `TikN.xlsx` (dòng máy tương ứng).
   - Kích hoạt runner nền chính thức:
     ```bash
     python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>
     ```
   - Chờ tiến trình nền kết thúc (Event-Driven Wakeup qua `notify_on_complete: true`).
   - Lấy screencap màn hình máy thật, dùng `browser_vision` soi mắt kiểm tra (Gate 6) thumbnail avatar mới trên trang Sửa hồ sơ / Profile, gửi `MEDIA:<path>` chứng minh thực tế.
